# -*- coding: utf-8 -*-
"""
AI量化策略信息服务平台 —— Streamlit主程序
"""

import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, '.')
from strategies.strategy_a import strategy_multi_factor
from strategies.strategy_b import strategy_trend_momentum
from strategies.strategy_c import strategy_mean_reversion
from engine.backtest import run_backtest
from llm_helper import recommend_strategy, risk_warning, compare_analysis

st.set_page_config(page_title="AI量化策略平台", page_icon="📊", layout="wide")

PAGES = ["🏠 首页", "📋 风险测评", "🎯 AI策略推荐", "📈 策略详情", "📊 策略对比"]


def go_to_page(idx):
    st.session_state['pending_page'] = idx
    st.rerun()


# ====================== 数据 ======================
@st.cache_data(ttl=600)
def load_stock_list():
    path = "data/stock_list.csv"
    if os.path.exists(path):
        df = pd.read_csv(path, dtype={'code': str})
        df['code'] = df['code'].str.zfill(6)
        return {row['code']: row['name'] for _, row in df.iterrows()}
    return {"600900": "长江电力", "600519": "贵州茅台", "300750": "宁德时代",
            "600036": "招商银行", "000858": "五粮液"}


@st.cache_data(ttl=600)
def load_data(code):
    code = str(code).zfill(6)
    path = f"data/prices/{code}.csv"
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=['date'])
    return None


def get_stock_label(code, name):
    return f"{name} ({code})"


@st.cache_data(ttl=600)
def load_latest_signals():
    path = "data/latest_signals.csv"
    if os.path.exists(path):
        df = pd.read_csv(path, dtype={'code': str})
        df['code'] = df['code'].str.zfill(6)
        return df
    return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_backtest_result(code):
    data = load_data(code)
    if data is None or len(data) < 200:
        return None
    results = {}
    for name, func in [("策略A-多因子", strategy_multi_factor),
                       ("策略B-趋势动量", strategy_trend_momentum),
                       ("策略C-均值回复", strategy_mean_reversion)]:
        r = run_backtest(func, data.copy())
        results[name] = r
    return results


STOCKS = load_stock_list()
STOCK_OPTIONS = [get_stock_label(c, n) for c, n in STOCKS.items()]
DEFAULT_CODE = "600900"  # 长江电力，预加载的展示标的


@st.cache_data(ttl=3600)
def load_backtest_metrics():
    path = "data/backtest_metrics.csv"
    if os.path.exists(path):
        df = pd.read_csv(path, dtype={'code': str})
        df['code'] = df['code'].str.zfill(6)
        return df
    return pd.DataFrame()


@st.cache_data(ttl=600)
def get_latest_prices():
    """返回每只股票的最新收盘价"""
    prices = {}
    for code in STOCKS:
        path = f"data/prices/{str(code).zfill(6)}.csv"
        if os.path.exists(path):
            df = pd.read_csv(path)
            if len(df) > 0:
                prices[str(code).zfill(6)] = df['close'].iloc[-1]
    return prices


def show_table(df, **kwargs):
    """展示表格：评分列四舍五入到1位小数"""
    df = df.copy()
    for col in df.columns:
        if "评分" in col or "signal" in col.lower():
            df[col] = df[col].round(1)
    return st.dataframe(df, **kwargs)

# ====================== 风险测评 ======================
# 参考证监会《投资者适当性管理办法》+ 银行/券商风险测评实践
# 三维度：财务状况(2题) + 投资经验(3题) + 风险态度(5题)
RISK_QUESTIONS = [
    # ---- 财务状况：承担风险的能力 ----
    ("您的年收入（或家庭年收入）", [
        "10万元以下",
        "10-25万元",
        "25-50万元",
        "50万元以上",
    ]),
    ("本次投资金额占您可投资资产的比例", [
        "超过70%，几乎是全部可投资资产",
        "30%-70%，占较大比重",
        "10%-30%，占比较小",
        "10%以下，不影响正常生活",
    ]),

    # ---- 投资经验：理解风险的能力 ----
    ("您进行股票或基金投资的年限", [
        "没有投资经验",
        "1年以内",
        "1-5年",
        "5年以上",
    ]),
    ("您曾经持有过的最大亏损幅度（含浮亏未卖出）", [
        "从未亏损超过5%",
        "亏损过5%-15%",
        "亏损过15%-30%",
        "亏损超过30%",
    ]),
    ("当您的持仓出现较大亏损时，您通常的做法", [
        "立即全部卖出，不再关注",
        "卖出一部分，降低心理压力",
        "继续持有，相信最终会回本",
        "分析亏损原因，如果逻辑没变就加仓摊薄成本",
    ]),

    # ---- 风险态度：承担风险的意愿 ----
    ("您本次投资的预期持有期限", [
        "6个月以内，随时可能要用钱",
        "6个月至1年",
        "1年至3年",
        "3年以上，不着急用",
    ]),
    ("您更倾向于哪种投资方式", [
        "保本优先，收益能跑赢存款就行",
        "大部分稳健配置，小部分博取弹性收益",
        "均衡配置，愿意承受波动换取中长期增长",
        "积极进取，愿意重仓看好的方向博取超额回报",
    ]),
    ("假设您在三个月前投入10万元，由于市场波动目前仅剩7.2万元", [
        "无法接受，会立刻全部赎回并停止投资",
        "焦虑但忍痛赎回一半，留一半观望",
        "虽然不安但继续持有，相信市场会修复",
        "检查策略逻辑是否仍然有效，如果有效则考虑逢低加仓",
    ]),
    ("以下哪种描述最符合您对'风险'的真实感受", [
        "一想到本金可能亏损，我就非常不安",
        "我能接受短期小幅波动，但不能容忍持续亏损",
        "我知道高风险高回报的道理，愿意为更高收益承担明显波动",
        "我认为波动本身也是机会，大幅回撤意味着更好的入场时机",
    ]),
    ("您期望的年化收益率是多少", [
        "3%-5%，跑赢银行理财就行",
        "5%-10%，略高于通胀",
        "10%-20%，愿意为此承受较大波动",
        "20%以上，追求显著超额收益",
    ]),
]

# 总分 10-40 分
def get_risk_level(score):
    if score <= 18: return "保守型", "🔵"
    elif score <= 26: return "稳健型", "🟢"
    elif score <= 34: return "平衡型", "🟡"
    return "进取型", "🔴"

FINISHED_DESC = {
    "保守型": "本金安全压倒一切。您对亏损的容忍度极低，投资期限较短，适合以风控为核心的策略。",
    "稳健型": "追求稳定增值，可以接受温和波动。您有一定投资经验，但更看重睡得安稳。",
    "平衡型": "理解风险收益的对等关系，愿意用可控波动换取更高的长期回报。",
    "进取型": "对市场波动有充分心理准备，能承受较大回撤，追求显著超额收益。",
}


def get_recommendation(risk_level):
    mapping = {
        "保守型": (["策略C（均值回复复合）"], "策略C回撤最小，在熊市中反而可能盈利。宁可不赚不愿多亏。"),
        "稳健型": (["策略A（多因子综合）", "策略C（均值回复复合）"], "多因子分散风险打底，均值回复控制回撤。兼顾收益与安全。"),
        "平衡型": (["策略A（多因子综合）", "策略B（趋势动量复合）"], "均衡配置。A打底，B在趋势行情中增强收益。"),
        "进取型": (["策略B（趋势动量复合）", "策略D（LLM新闻情绪）"], "趋势追涨爆发力强，AI情绪捕捉事件驱动机会。"),
    }
    return mapping.get(risk_level, (["策略A"], ""))


# ====================== 页面1：首页 ======================
def page_home():
    st.title("📊 AI量化策略信息服务平台")
    st.caption("用AI帮您看懂量化策略 —— 不是告诉您买什么，而是帮您看清楚每个策略的真实面貌")

    st.divider()
    st.markdown("### 三步走：测评 → AI推荐 → 查看回测数据")

    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.markdown("#### 📋 第一步：风险测评")
            st.caption("10道专业测评题，2分钟完成。判断您的风险承受能力，确保策略推荐不是盲目的。")
    with col2:
        with st.container(border=True):
            st.markdown("#### 🤖 第二步：AI推荐")
            st.caption("系统根据您的测评结果，从四个策略中匹配最适合的组合，并解释推荐理由。")
    with col3:
        with st.container(border=True):
            st.markdown("#### 📈 第三步：数据说话")
            st.caption("每个策略都有完整的回测数据。净值曲线、收益、回撤、胜率——全透明展示。")

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        amount = st.number_input("投资金额（元）", min_value=1000, value=100000, step=10000)
    with col_b:
        horizon = st.selectbox("投资期限", ["3个月以内", "6个月到1年", "1-3年", "3年以上"])

    st.session_state['amount'] = amount
    st.session_state['horizon'] = horizon

    st.divider()

    if st.button("👉 开始风险测评", type="primary", width='stretch'):
        go_to_page(1)


# ====================== 页面2：风险测评 ======================
def page_assessment():
    st.title("📋 风险承受能力测评")
    st.caption("10道选择题，做完自动出结果。参考了证监会《证券期货投资者适当性管理办法》")

    # 初始化
    if 'answers' not in st.session_state:
        st.session_state['answers'] = {}
    if 'reset_ver' not in st.session_state:
        st.session_state['reset_ver'] = 0

    scores = []
    for i, (q, options) in enumerate(RISK_QUESTIONS):
        st.markdown(f"**{i+1}. {q}**")
        prev_idx = st.session_state['answers'].get(i)
        ans = st.radio("", options, key=f"q{st.session_state['reset_ver']}_{i}",
                       index=prev_idx, label_visibility="collapsed")
        if ans:
            st.session_state['answers'][i] = options.index(ans)
            scores.append(options.index(ans) + 1)

    st.divider()

    if len(scores) == 10:
        total = sum(scores)
        level, emoji = get_risk_level(total)
        with st.container(border=True):
            st.success(f"### {emoji} {level}（{total}/40分）")
            st.caption(FINISHED_DESC.get(level, ''))

        st.session_state['risk_level'] = level
        st.session_state['risk_score'] = total
        # 保存答题详情供LLM使用
        st.session_state['risk_answers'] = [
            f"{RISK_QUESTIONS[i][0][:10]}：{options[st.session_state['answers'][i]]}"
            for i, (_, options) in enumerate(RISK_QUESTIONS)
            if i in st.session_state.get('answers', {})
        ]

        st.info("💡 接下来，系统将根据您的风险等级，匹配最适合的量化策略，并展示真实的历史回测数据供您参考。")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🎯 查看AI策略推荐", type="primary", width='stretch'):
                go_to_page(2)
        with col_b:
            if st.button("🔄 重新测评", width='stretch'):
                st.session_state['answers'] = {}
                st.session_state['reset_ver'] += 1
                st.rerun()
    else:
        st.info(f"已完成 {len(scores)}/10 题，请继续...")


# ====================== 页面3：AI策略推荐 ======================
def page_recommend():
    st.markdown("<script>window.scrollTo(0,0);</script>", unsafe_allow_html=True)
    st.title("🎯 AI策略推荐")

    if 'risk_level' not in st.session_state:
        st.warning("请先完成风险测评")
        if st.button("去测评", type="primary"):
            go_to_page(1)
        return

    level = st.session_state['risk_level']
    amount = st.session_state.get('amount', 100000)
    horizon = st.session_state.get('horizon', '6个月到1年')

    # ---- 用户画像 ----
    c1, c2, c3 = st.columns(3)
    c1.metric("风险等级", level)
    c2.metric("投资金额", f"{amount:,}元")
    c3.metric("投资期限", horizon)

    st.divider()

    # ---- AI推荐 ----
    strategies, fallback_reason = get_recommendation(level)
    st.subheader(f"推荐策略：{' + '.join(strategies)}")

    # LLM生成推荐理由
    with st.spinner("AI正在分析您的画像..."):
        demo_r = get_backtest_result(DEFAULT_CODE)
        signals_df = load_latest_signals()
        top_stocks_str = ""
        if demo_r is not None and not signals_df.empty:
            summary = "\n".join([
                f"{n}：年化{r['annual_return']:+.2f}%，最大回撤{r['max_drawdown']:.2f}%"
                for n, r in demo_r.items()
            ])
            # 找推荐策略对应的信号列
            strat_to_col = {
                "策略A": "signal_A", "策略B": "signal_B", "策略C": "signal_C",
                "多因子综合评分": "signal_A", "趋势动量复合": "signal_B", "均值回复复合": "signal_C",
            }
            prices = get_latest_prices()
            for strat_name in strategies:
                for key, col in strat_to_col.items():
                    if key in strat_name and col in signals_df.columns:
                        top3 = signals_df.nlargest(3, col)[["name", "code", col]]
                        items = []
                        for _, row in top3.iterrows():
                            c = str(row['code']).zfill(6)
                            price = prices.get(c, 0)
                            min_buy = int(price * 100)
                            items.append(f"{row['name']}(现价{price:.0f}元，1手{min_buy:,}元，评分{row[col]:.0f})")
                        top_stocks_str = "、".join(items)
                        break
            llm_reason = recommend_strategy(level, amount, horizon,
                ' + '.join(strategies), summary, top_stocks_str,
                st.session_state.get('risk_score'),
                st.session_state.get('risk_answers', []))
        else:
            llm_reason = None

    if llm_reason:
        with st.container(border=True):
            st.markdown(f"🤖 {llm_reason}")
            st.caption("以上推荐由AI生成")
    else:
        with st.container(border=True):
            st.markdown(f"💡 {fallback_reason}")

    st.divider()

    # ---- 回测验证（在信号之前，让用户立刻看到推荐策略的数据） ----
    st.subheader("📈 回测验证")
    st.caption(f"以长江电力为例，看看推荐策略的历史表现如何")

    with st.spinner("正在加载回测数据..."):
        demo_results = get_backtest_result(DEFAULT_CODE)

    if demo_results is not None:
        # 三列并排展示指标卡片
        cols = st.columns(3)
        for i, (name, r) in enumerate(demo_results.items()):
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"**{name}**")
                    amt_loss = int(100000 * abs(r['max_drawdown']) / 100)
                    st.metric("年化收益", f"{r['annual_return']:+.2f}%")
                    st.metric("最大回撤", f"{r['max_drawdown']:.2f}%")
                    st.caption(f"10万最多亏{amt_loss:,}元 | 夏普: {r['sharpe_ratio']:.3f} | 胜率: {r['win_rate']:.1f}%")
        st.caption("")

        col_a, col_b = st.columns(2)
        with col_a:
            st.caption(f"👆 {STOCKS[DEFAULT_CODE]}是沪深300代表性标的，以上数据均为真实回测结果。")
        with col_b:
            if st.button("📈 查看其他股票 → 策略详情页", type="primary"):
                go_to_page(3)
    else:
        st.warning("回测数据暂不可用")

    st.divider()

    # ---- 今日信号（在回测后面） ----
    st.subheader("📡 今日策略信号")
    st.caption("策略A/B/C对40只股票的最新评分排名。策略D（LLM新闻情绪）需实时新闻数据，暂独立运行")

    signals_df = load_latest_signals()
    if not signals_df.empty:
        with st.expander("📖 怎么看这张表？点击展开"):
            st.markdown(f"""
            **您的风险等级：{risk_level}**——表格已按此等级自动排序：
            - 保守型 → 优先看**最大回撤**小的股票（亏得少最重要）
            - 稳健型 → 优先看**夏普**高的股票（每份风险换来的回报最高）
            - 平衡型 → 优先看**年化收益**高的股票（愿意承受波动博收益）
            - 进取型 → 优先看**信号评分**高的股票（敢追最强的信号）

            **三个策略评分的含义：**
            - 策略A（多因子）：五个维度综合打分，靠排名选股。Top 5为推荐，Bottom 5谨慎
            - 策略B（趋势动量）：判断趋势质量和可持续性。>60趋势明确，<40趋势弱或反转
            - 策略C（均值回复）：找超跌反弹机会。>55有超卖信号，大部分时间在35-55之间

            **回测数据说明：** 年化收益、最大回撤、夏普比率均来自2020年1月至今的真实回测。历史回测不代表未来表现。
            """)

        strategy_cols = [
            ("📊 策略A · 多因子综合", "signal_A"),
            ("📈 策略B · 趋势动量", "signal_B"),
            ("🔄 策略C · 均值回复", "signal_C"),
        ]
        tabs = st.tabs([s[0] for s in strategy_cols])

        prices = get_latest_prices()
        metrics_df = load_backtest_metrics()
        risk_level = st.session_state.get('risk_level', '稳健型')

        for tab, (title, col) in zip(tabs, strategy_cols):
            with tab:
                # 合并信号评分+回测指标
                s_name = col.replace("signal_", "")  # "signal_A" -> "A"
                ranked = signals_df[["name", "code", col]].copy()
                ranked.columns = ["股票名称", "代码", "评分"]
                ranked["最低买入"] = ranked["代码"].apply(
                    lambda c: f"{prices.get(str(c).zfill(6), 0) * 100 / 10000:.1f}万"
                )

                # 合并回测指标
                if not metrics_df.empty:
                    m = metrics_df[metrics_df['strategy'] == s_name][
                        ['code', 'annual_return', 'max_drawdown', 'sharpe_ratio']
                    ].copy()
                    m.columns = ['代码', '年化收益', '最大回撤', '夏普']
                    ranked = ranked.merge(m, on='代码', how='left')
                    ranked["年化收益"] = ranked["年化收益"].apply(
                        lambda x: f"{x:+.1f}%" if pd.notna(x) else "-")
                    ranked["最大回撤"] = ranked["最大回撤"].apply(
                        lambda x: f"{x:.1f}%" if pd.notna(x) else "-")
                    ranked["夏普"] = ranked["夏普"].apply(
                        lambda x: f"{x:.2f}" if pd.notna(x) else "-")

                # 按风险等级排序
                if risk_level == "保守型" and "最大回撤" in ranked.columns:
                    ranked = ranked.sort_values("最大回撤", ascending=True)
                elif risk_level == "稳健型" and "夏普" in ranked.columns:
                    ranked = ranked.sort_values("夏普", ascending=False)
                elif risk_level == "平衡型" and "年化收益" in ranked.columns:
                    ranked = ranked.sort_values("年化收益", ascending=False)
                else:
                    ranked = ranked.sort_values("评分", ascending=False)

                # 默认排序提示
                sort_hints = {"保守型": "按最大回撤从小到大", "稳健型": "按夏普从高到低",
                              "平衡型": "按年化收益从高到低", "进取型": "按信号评分从高到低"}
                st.caption(f"排序方式：{sort_hints.get(risk_level, '按评分')}")

                if col == "signal_A":
                    # 策略A排名制：Top5 / 中等 / Bottom5
                    top_n = min(5, len(ranked))
                    mid_start = top_n
                    mid_end = min(15, len(ranked))
                    bot_start = max(0, len(ranked) - 5)
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.success("🟢 综合评分 Top 5")
                        if top_n > 0:
                            show_table(ranked.head(top_n), hide_index=True, width='stretch')
                        else:
                            st.caption("暂无")
                    with c2:
                        st.info("🟡 中等（第6-15名）")
                        if mid_end > mid_start:
                            show_table(ranked.iloc[mid_start:mid_end], hide_index=True, width='stretch')
                        else:
                            st.caption("暂无")
                    with c3:
                        st.error("🔴 排名靠后（Bottom 5）")
                        if bot_start < len(ranked):
                            show_table(ranked.tail(5), hide_index=True, width='stretch')
                        else:
                            st.caption("暂无")
                elif col == "signal_C":
                    hi, mid = 55, 35
                    good = ranked[ranked["评分"] >= hi]
                    normal = ranked[(ranked["评分"] >= mid) & (ranked["评分"] < hi)]
                    bad = ranked[ranked["评分"] < mid]
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.success(f"🟢 超卖反弹信号（≥{hi}）")
                        if len(good) > 0:
                            show_table(good, hide_index=True, width='stretch')
                            st.caption(f"{len(good)} 只")
                        else:
                            st.caption("暂无")
                    with c2:
                        st.info(f"🟡 一般（{mid}-{hi-1}）")
                        if len(normal) > 0:
                            show_table(normal, hide_index=True, width='stretch')
                            st.caption(f"{len(normal)} 只")
                        else:
                            st.caption("暂无")
                    with c3:
                        st.error(f"🔴 回避（<{mid}）")
                        if len(bad) > 0:
                            show_table(bad, hide_index=True, width='stretch')
                            st.caption(f"{len(bad)} 只")
                        else:
                            st.caption("暂无")
                else:
                    hi, mid = 60, 40
                    good = ranked[ranked["评分"] >= hi]
                    normal = ranked[(ranked["评分"] >= mid) & (ranked["评分"] < hi)]
                    bad = ranked[ranked["评分"] < mid]
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.success(f"🟢 买入信号（≥{hi}）")
                        if len(good) > 0:
                            show_table(good, hide_index=True, width='stretch')
                            st.caption(f"{len(good)} 只")
                        else:
                            st.caption("暂无")
                    with c2:
                        st.info(f"🟡 一般观望（{mid}-{hi-1}）")
                        if len(normal) > 0:
                            show_table(normal, hide_index=True, width='stretch')
                            st.caption(f"{len(normal)} 只")
                        else:
                            st.caption("暂无")
                    with c3:
                        st.error(f"🔴 回避（<{mid}）")
                        if len(bad) > 0:
                            show_table(bad, hide_index=True, width='stretch')
                            st.caption(f"{len(bad)} 只")
                        else:
                            st.caption("暂无")
    else:
        st.warning("暂无信号数据，请先运行 data/compute_signals.py")

    st.divider()
    st.caption("💡 最低买入 = 最新股价 × 100股（A股最低交易1手）。请根据自己的投资金额判断能否买入。")
    st.caption("⚠️ 历史回测不代表未来表现。请根据自身情况独立判断。")


# ====================== 页面4：策略详情 ======================
def page_detail():
    st.markdown("<script>window.scrollTo(0,0);</script>", unsafe_allow_html=True)
    st.title("📈 策略详情")

    stock = st.selectbox("选择股票", STOCK_OPTIONS, key="detail_stock")
    code = stock.split("(")[1].rstrip(")")

    if st.button("开始分析", type="primary"):
        with st.spinner(f"正在对 {stock} 运行三个策略回测..."):
            results = get_backtest_result(code)

        if results is not None:
            for name, r in results.items():
                with st.expander(f"**{name}** — 年化收益 {r['annual_return']:+.2f}%", expanded=True):
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("年化收益", f"{r['annual_return']:+.2f}%")
                    c2.metric("最大回撤", f"{r['max_drawdown']:.2f}%")
                    c3.metric("夏普比率", f"{r['sharpe_ratio']:.3f}")
                    c4.metric("胜率", f"{r['win_rate']:.1f}%")
                    c5.metric("交易次数", r['trade_count'])

                    equity = r['equity_curve']
                    if len(equity) > 0:
                        st.line_chart(equity.set_index('date')['equity'], width='stretch')

                    max_loss = int(100000 * abs(r['max_drawdown']) / 100)
                    # 计算实际最差年份
                    eq = r['equity_curve'].copy()
                    eq['year'] = eq['date'].dt.year
                    yearly = eq.groupby('year').apply(
                        lambda g: (g['equity'].iloc[-1] / g['equity'].iloc[0] - 1) * 100
                    )
                    if len(yearly) > 0:
                        worst_year = yearly.idxmin()
                        worst_ret = yearly.min()
                    else:
                        worst_year, worst_ret = "2022", -12.1
                    llm_warn = risk_warning(
                        name, r['annual_return'], r['max_drawdown'],
                        r['win_rate'], str(worst_year), worst_ret
                    )
                    if llm_warn:
                        st.warning(f"⚠️ {llm_warn}")
                    else:
                        st.warning(
                            f"⚠️ 历史最大回撤 {r['max_drawdown']:.2f}%，"
                            f"即10万元最大亏损约 **{max_loss:,}元**。"
                            f"历史回测不代表未来表现。"
                        )
        else:
            st.warning("暂无该股票数据，请先运行数据采集脚本")


# ====================== 页面5：策略对比 ======================
def page_compare():
    st.markdown("<script>window.scrollTo(0,0);</script>", unsafe_allow_html=True)
    st.title("📊 策略对比")

    stock = st.selectbox("选择股票", STOCK_OPTIONS, key="compare_stock")
    code = stock.split("(")[1].rstrip(")")

    if st.button("生成对比报告", type="primary"):
        with st.spinner(f"正在对比 {stock} 的三个策略..."):
            results = get_backtest_result(code)

        if results is not None:
            rows = []
            for name, r in results.items():
                rows.append({
                    "策略": name,
                    "年化收益": f"{r['annual_return']:+.2f}%",
                    "最大回撤": f"{r['max_drawdown']:.2f}%",
                    "夏普比率": f"{r['sharpe_ratio']:.3f}",
                    "胜率": f"{r['win_rate']:.1f}%",
                    "交易次数": r['trade_count'],
                })
            show_table(pd.DataFrame(rows), width='stretch', hide_index=True)

            st.divider()
            st.subheader("📈 净值曲线对比")
            chart_data = pd.DataFrame()
            for name, r in results.items():
                eq = r['equity_curve'].set_index('date')['equity']
                chart_data[name] = eq
            st.line_chart(chart_data, width='stretch')

            llm_analysis = compare_analysis(stock, results,
                st.session_state.get('risk_level'))
            if llm_analysis:
                st.info(f"🤖 {llm_analysis}")
            else:
                vals = [(n, r['annual_return'], r['max_drawdown']) for n, r in results.items()]
                best_return = max(vals, key=lambda x: x[1])
                best_dd = min(vals, key=lambda x: abs(x[2]))
                st.info(
                    f"📊 **快速分析**：在{stock}上，"
                    f"**{best_return[0]}**收益最高（{best_return[1]:+.2f}%），"
                    f"**{best_dd[0]}**回撤控制最好（{best_dd[2]:.2f}%）。"
                    f"同一只股票、同一段时间，不同策略表现完全不同——"
                    f"这正是为什么需要先做风险测评，再选策略。"
                )
        else:
            st.warning("暂无该股票数据")


# ====================== 主入口 ======================
def main():
    if 'page' not in st.session_state:
        st.session_state['page'] = 0

    # 侧边栏
    with st.sidebar:
        st.title("📊 AI量化平台")
        st.caption("量化策略信息服务平台")
        st.divider()

        if 'pending_page' in st.session_state:
            target = st.session_state['pending_page']
            st.session_state['page'] = target
            st.session_state['nav_radio'] = PAGES[target]
            del st.session_state['pending_page']

        def on_nav_change():
            st.session_state['page'] = PAGES.index(st.session_state.nav_radio)

        page = st.radio("导航", PAGES, label_visibility="collapsed",
                        key="nav_radio", on_change=on_nav_change)

        st.divider()
        st.markdown("---")
        st.caption("⚠️ 历史回测不代表未来收益")
        st.caption("本平台不构成投资建议")

    # 预加载长江电力回测缓存
    get_backtest_result(DEFAULT_CODE)

    current = st.session_state.get('page', 0)

    if current == 0:
        page_home()
    elif current == 1:
        page_assessment()
    elif current == 2:
        page_recommend()
    elif current == 3:
        page_detail()
    elif current == 4:
        page_compare()


if __name__ == "__main__":
    main()
