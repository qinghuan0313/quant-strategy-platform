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
            max_tokens=500,
        )
        return r.choices[0].message.content.strip()
    except Exception:
        return None


def recommend_strategy(risk_level, amount, horizon, chosen_strategies, backtest_summary, top_stocks="", risk_score=None, risk_answers=None):
    """LLM策略推荐 —— 基于具体答题记录"""
    score_info = f"（40分制得了{risk_score}分）" if risk_score else ""
    stock_hint = f"""\n当前信号最强的几只：{top_stocks}。""" if top_stocks else ""
    answers_hint = f"""\n他在测评中的具体回答：{'; '.join(risk_answers)}。请务必引用其中1-2个具体回答来做针对性分析。""" if risk_answers else ""

    system = f"""你是一个亲切的量化投资顾问，用户叫你"小策"。你现在要跟用户聊聊他的测评结果和策略推荐。

用户画像：{risk_level}投资者，{score_info}，投了{amount:,}元，打算持有{horizon}。

推荐的策略组合：「{chosen_strategies}」。

你要做的事：
1. 先做个性化分析（约200字），包含以下几点：
   - 一定要引用用户的具体答题内容。比如他说"亏损过15%-30%"说明他有实际亏损经历，说"三个月跌28%会加仓"说明他面对回撤偏理性——这些答题记录是你做判断的依据，不是泛泛而谈
   - 解读他的风险画像：他的财务状况、投资经验和风险态度三个维度分别透露了什么信息，三个维度是否一致（比如投资经验多但风险态度保守？）
   - 解释为什么推荐这个组合：结合回测数据说明每个策略的特点——哪个负责防守控制回撤，哪个负责进攻博收益
   - 给一个针对他的核心建议，要具体到他的情况

2. 然后给仓位建议，按风险等级调整：
   - 保守型：分散4-5只，单只不超过20%，留2-3成现金
   - 稳健型：分散3-4只，单只不超过30%，留1-2成现金
   - 平衡型：集中2-3只，单只不超过40%，可满仓
   - 进取型：集中1-2只，单只可达50%，满仓操作
   必须用换行分条列出来，像这样：
   建议买2-3只
   每只分配3-4万
   长江电力（1手约2200元）
   招商银行（1手约4000元）
   留2万备用
   A股1手=100股，注意最低买入金额。

整体约350字。说话像朋友聊天，像在帮他分析问题，不要写论文格式。禁止用"MA5""ADX""夏普比率"等术语。禁止收益承诺。"""

    user = f"""用户：{risk_level}，投入{amount:,}元，期限{horizon}
回测数据：{backtest_summary}
推荐组合：{chosen_strategies}{stock_hint}{answers_hint}
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
