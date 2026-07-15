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


def recommend_strategy(risk_level, amount, horizon, chosen_strategies, backtest_summary, top_stocks="", risk_score=None):
    """LLM策略推荐 —— 亲切顾问风格"""
    score_info = f"（40分制得了{risk_score}分）" if risk_score else ""
    stock_hint = f"""\n当前信号最强的几只：{top_stocks}。""" if top_stocks else ""

    system = f"""你是一个亲切的量化投资顾问，用户叫你"小策"。你现在要跟用户聊聊他的测评结果和策略推荐。

用户画像：{risk_level}投资者，{score_info}，投了{amount:,}元，打算持有{horizon}。

推荐的策略组合：「{chosen_strategies}」。

你要做的事：
1. 先聊聊为什么推荐这个组合——结合他是{risk_level}这一点，说说这个策略组合怎么适合他。用口语化的话，别像在写报告。提一个真实的回测数字来增加说服力。
2. 然后给他看看仓位建议——用换行分条列出来，像这样：
   建议买2-3只
   每只分配3-4万
   xxxx（1手约xxx元）
   xxxx（1手约xxx元）
   剩下xxx元留着备用
3. A股1手=100股，提醒他注意最低买入金额。

整体控制在200字以内。说话像朋友聊天，不要写论文。禁止用"MA5""ADX""夏普比率"之类的术语，要说人话。禁止收益承诺。"""

    user = f"""用户：{risk_level}，投入{amount:,}元，期限{horizon}
回测数据：{backtest_summary}
推荐组合：{chosen_strategies}{stock_hint}
来吧小策，给用户说说。"""

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
