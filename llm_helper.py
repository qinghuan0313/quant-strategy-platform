# -*- coding: utf-8 -*-
"""LLM调用封装 —— 策略推荐 + 风险提示 + 对比分析"""

import os


def _get_api_key():
    """读取API密钥：Streamlit Cloud从secrets读，本地从文件读"""
    try:
        import streamlit as st
        return st.secrets["deepseek_api_key"]
    except Exception:
        pass
    path = "apikey.txt"
    if os.path.exists(path):
        with open(path, "r") as f:
            return f.read().strip()
    return None


def llm_chat(system_prompt, user_prompt):
    """通用LLM调用，失败返回None"""
    api_key = _get_api_key()
    if api_key is None:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        r = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        return r.choices[0].message.content.strip()
    except Exception:
        return None


def recommend_strategy(risk_level, amount, horizon, chosen_strategies, backtest_summary, risk_score=None):
    """LLM策略推荐 —— 真正个性化"""
    score_info = f"，测评得分{risk_score}/32分" if risk_score else ""
    system = f"""你是量化投资顾问。系统已为用户选定了策略组合「{chosen_strategies}」。
请为这个用户写推荐理由。必须是针对这个具体用户的，不能是套话。

要求：
1. 根据用户{risk_level}{score_info}的特点，解释为什么这个策略组合合适
   - 保守型重点说"回撤小、睡得安稳"
   - 进取型重点说"能承受波动、博取高收益"
2. 根据投资期限{horizon}给建议——短期(<6个月)提醒频繁调仓风险，长期(>1年)可以忽略短期波动
3. 引用回测真实数字，用绝对金额说风险
4. 禁止术语、禁止收益承诺
5. 150字以内，像真人在聊天"""

    user = f"""用户：{risk_level}，投入{amount:,}元，期限{horizon}
回测数据：{backtest_summary}
推荐组合：{chosen_strategies}
请写推荐理由。"""

    return llm_chat(system, user)


def risk_warning(strategy_name, annual_ret, max_dd, win_rate, worst_year, worst_year_ret):
    """LLM风险提示"""
    system = """你是风险提示专家。根据回测数据生成风险提示。
要求：
1. 第一句用绝对金额说最大亏损
2. 提及最差年份
3. 80字以内，不用客套话"""

    user = f"""{strategy_name}：年化{annual_ret:+.2f}%，最大回撤{max_dd:.2f}%，
胜率{win_rate:.1f}%，最差年份{worst_year}年收益{worst_year_ret:+.2f}%"""

    return llm_chat(system, user)


def compare_analysis(stock_name, results, risk_level=None):
    """LLM策略对比分析 —— 结合用户风险等级"""
    risk_hint = f"用户是{risk_level}，请在分析时特别关注回撤数据。" if risk_level else ""
    system = f"""你是量化策略分析师。请对比三个策略在同一只股票上的表现，给出一段分析。
{risk_hint}
要求：
1. 不只是"A收益最高B回撤最小"，要解释原因
   - 如果趋势策略最好→说明该股票趋势性强
   - 如果均值回复最好→说明该股票波动大、经常超跌反弹
   - 如果多因子最好→说明该股票适合基本面驱动
2. 结合用户风险等级给出针对性建议
3. 100字以内，有洞察力"""

    summary = "\n".join([
        f"{n}：年化{r['annual_return']:+.2f}%，回撤{r['max_drawdown']:.2f}%，夏普{r['sharpe_ratio']:.3f}"
        for n, r in results.items()
    ])
    user = f"在{stock_name}上：\n{summary}\n请分析三个策略的表现差异。"

    return llm_chat(system, user)
