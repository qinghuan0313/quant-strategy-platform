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


def recommend_strategy(risk_level, amount, horizon, backtest_summary):
    """LLM策略推荐"""
    system = """你是量化投资顾问。根据用户画像和回测数据推荐策略。
要求：
1. 用通俗语言，不给"MA5上穿MA20"这种术语
2. 引用真实的回测数字
3. 用绝对金额说风险——"10万最多亏1.3万"而不是"-13%"
4. 禁止"保证收益""稳赚不赔""建议买入"
5. 150字以内"""

    user = f"""用户：{risk_level}，投入{amount:,}元，期限{horizon}
各策略历史回测数据：
{backtest_summary}
请推荐最合适的策略组合。"""

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


def compare_analysis(stock_name, results):
    """LLM策略对比分析"""
    system = """你是量化策略分析师。对比不同策略的表现，给出一段分析。
要求：有洞察，不只是"X最高Y最低"，要解释为什么。100字以内。"""

    summary = "\n".join([
        f"{n}：年化{r['annual_return']:+.2f}%，回撤{r['max_drawdown']:.2f}%，夏普{r['sharpe_ratio']:.3f}"
        for n, r in results.items()
    ])
    user = f"在{stock_name}上：\n{summary}\n请分析三个策略的表现差异。"

    return llm_chat(system, user)
