# -*- coding: utf-8 -*-
"""
策略D：LLM新闻情绪驱动
核心逻辑：用大模型分析财经新闻情感 → 合成日度情绪因子 → 产生交易信号
与策略A/B/C不同，这个策略的数据源是新闻文本，不是价格

三个步骤：
  1. 对每只股票的每日新闻调用LLM，返回情感分数（-100到+100）
  2. 聚合：一只股票当天所有新闻情感分取平均 → 日度情绪因子
  3. 信号：连续3天情绪>+20 → 买入，连续3天<-20 → 卖出
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import time


# ====================== LLM调用封装 ======================

def call_llm_sentiment(news_title, news_content, api_key=None, base_url=None, model=None):
    """
    调用LLM分析单条新闻的情感

    参数：
        news_title: 新闻标题
        news_content: 新闻正文
        api_key: API密钥（DeepSeek或通义千问）
        base_url: API地址
        model: 模型名称

    返回：
        dict: {"sentiment": "positive"|"negative"|"neutral",
               "score": -100~100,
               "reason": "一句话理由"}
    """
    # 如果没有配置API，用规则兜底
    if api_key is None:
        return _rule_based_sentiment(news_title, news_content)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url)

        prompt = """你是金融情感分析专家。分析以下财经新闻对股价的影响。

请输出JSON格式，不要输出其他内容：
{
  "sentiment": "positive" / "negative" / "neutral",
  "score": -100到100的整数（-100最强利空，+100最强利好），
  "reason": "一句话理由（20字以内）"
}

规则：
1. 实质性利好（业绩超预期、产品涨价、政策扶持）score>50
2. 温和利好（订单增加、研报看好）score 20-50
3. 中性消息（人事变动、例行公告）score -10到+10
4. 温和利空（减持、诉讼、增速放缓）score -50到-20
5. 重大利空（业绩暴雷、处罚、退市风险）score<-50
6. 只输出JSON，不要加任何解释文字"""

        response = client.chat.completions.create(
            model=model or "deepseek-chat",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"新闻标题：{news_title}\n新闻正文：{news_content[:500]}"}
            ],
            temperature=0.1,
            max_tokens=200
        )

        result_text = response.choices[0].message.content.strip()
        # 清理可能的markdown标记
        if result_text.startswith("```"):
            result_text = result_text.split("\n", 1)[1]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
        result = json.loads(result_text)
        return result

    except Exception as e:
        print(f"  LLM调用失败: {e}，回退到规则兜底")
        return _rule_based_sentiment(news_title, news_content)


def _rule_based_sentiment(title, content):
    """
    规则兜底：LLM不可用时用关键词判断情感
    外文同学设计的Prompt用于LLM，这是降级方案
    """
    text = title + " " + content

    # 正面关键词
    positive_words = [
        "增长", "上涨", "突破", "创新高", "超预期", "扭亏", "盈利",
        "分红", "回购", "增持", "中标", "订单", "涨价", "扩产",
        "获批", "政策支持", "补贴", "专利", "技术突破", "合作",
        "上调评级", "买入评级", "看好", "布局", "签约"
    ]

    # 负面关键词
    negative_words = [
        "下跌", "亏损", "下滑", "减持", "诉讼", "处罚", "退市",
        "跌停", "违约", "停产", "裁员", "调查", "违规", "暴雷",
        "商誉减值", "计提", "业绩预告下降", "下调评级", "卖出评级",
        "资金链", "逾期", "查封", "冻结", "问询函", "警示函"
    ]

    pos_count = sum(1 for w in positive_words if w in text)
    neg_count = sum(1 for w in negative_words if w in text)

    if pos_count > neg_count:
        score = min(80, pos_count * 20)
        return {"sentiment": "positive", "score": score, "reason": f"命中{pos_count}个正面关键词"}
    elif neg_count > pos_count:
        score = -min(80, neg_count * 20)
        return {"sentiment": "negative", "score": score, "reason": f"命中{neg_count}个负面关键词"}
    else:
        return {"sentiment": "neutral", "score": 0, "reason": "未命中明确情感关键词"}


# ====================== 情感因子合成 ======================

def aggregate_daily_sentiment(news_df, date_col='date', score_col='score'):
    """
    将单条新闻的情感分数聚合成日度因子

    参数：
        news_df: DataFrame，包含 date, score 列
        date_col: 日期列名
        score_col: 情感分数列名

    返回：
        DataFrame，包含 date, sentiment_factor, news_count
    """
    daily = news_df.groupby(date_col).agg(
        sentiment_factor=(score_col, 'mean'),
        news_count=(score_col, 'count')
    ).reset_index()

    # 新闻太少的日子，向0收缩（避免单条新闻误差）
    daily['confidence'] = 1 - np.exp(-daily['news_count'] / 3)
    daily['sentiment_factor'] = daily['sentiment_factor'] * daily['confidence']

    return daily


def strategy_llm_sentiment(data, news_data=None, api_key=None, base_url=None, model=None):
    """
    策略D：LLM新闻情绪驱动

    参数：
        data: DataFrame，包含 date, open, close, high, low, volume
        news_data: DataFrame，包含 date, title, content（已获取的新闻）
                  如果为None，返回中性信号
        api_key: LLM API密钥
        base_url: LLM API地址
        model: 模型名称

    返回：
        DataFrame，添加 signal 列（0-100评分）
    """
    df = data.copy()
    df['signal'] = 50.0

    if news_data is None or news_data.empty:
        return df

    # Step 1: 对每条新闻做情感分析（带缓存）
    sentiment_results = []
    cache_file = 'data/sentiment_cache.csv'

    # 加载已有缓存
    cache = {}
    if os.path.exists(cache_file):
        cache_df = pd.read_csv(cache_file)
        for _, row in cache_df.iterrows():
            cache[row['title_hash']] = {
                'sentiment': row['sentiment'],
                'score': row['score'],
                'reason': row['reason']
            }

    for _, news in news_data.iterrows():
        title = news.get('title', '')
        content = news.get('content', '')
        title_hash = str(hash(title))

        if title_hash in cache:
            sentiment_results.append(cache[title_hash])
        else:
            result = call_llm_sentiment(title, content, api_key, base_url, model)
            result['title_hash'] = title_hash
            sentiment_results.append(result)
            cache[title_hash] = result

            # 调用间隔，避免API限流
            time.sleep(0.5)

    # 保存缓存
    cache_rows = [{'title_hash': h, 'sentiment': r['sentiment'],
                    'score': r['score'], 'reason': r['reason']}
                  for h, r in cache.items()]
    pd.DataFrame(cache_rows).to_csv(cache_file, index=False)

    # Step 2: 合成日度情感因子
    sentiment_df = news_data[['date']].copy()
    sentiment_df['score'] = [r['score'] for r in sentiment_results]

    daily_sentiment = aggregate_daily_sentiment(sentiment_df)

    # Step 3: 根据情感因子生成信号
    # 将日度情感映射到行情数据的日期上
    df['date'] = pd.to_datetime(df['date'])
    daily_sentiment['date'] = pd.to_datetime(daily_sentiment['date'])

    # 合并
    df = df.merge(daily_sentiment[['date', 'sentiment_factor']], on='date', how='left')
    df['sentiment_factor'] = df['sentiment_factor'].fillna(0)

    # 计算情感因子的3日移动平均（平滑噪声）
    df['sent_ma3'] = df['sentiment_factor'].rolling(3, min_periods=1).mean()
    df['sent_ma5'] = df['sentiment_factor'].rolling(5, min_periods=1).mean()

    for idx in range(len(df)):
        sent = df['sentiment_factor'].iloc[idx]
        sent_ma3 = df['sent_ma3'].iloc[idx]

        if sent_ma3 > 40:
            signal_score = 85   # 持续强正面情绪
        elif sent_ma3 > 20:
            signal_score = 65 + (sent_ma3 - 20)   # 温和正面
        elif sent_ma3 > 5:
            signal_score = 55   # 略偏正面
        elif sent_ma3 > -5:
            signal_score = 50   # 中性
        elif sent_ma3 > -20:
            signal_score = 40   # 略偏负面
        elif sent_ma3 > -40:
            signal_score = 25   # 温和负面
        else:
            signal_score = 15   # 持续强负面

        # 单日极端值修正
        if abs(sent) > 60:
            signal_score += (10 if sent > 0 else -10)
            signal_score = max(0, min(100, signal_score))

        df.loc[df.index[idx], 'signal'] = round(signal_score, 1)

    # 清理
    df.drop(columns=['sentiment_factor', 'sent_ma3', 'sent_ma5'], inplace=True, errors='ignore')
    return df
