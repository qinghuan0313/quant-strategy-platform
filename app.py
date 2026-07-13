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


def centered_dataframe(df, **kwargs):
    return st.dataframe(
        df.style.set_table_styles(
            [dict(selector='td,th', props=[('text-align', 'center')])]
        ),
        **kwargs
    )

# ====================== 风险测评 ======================
RISK_QUESTIONS = [
    ("您的年龄", ["60岁以上", "45-60岁", "30-45岁", "18-30岁"]),
    ("您的年收入", ["5万元以下", "5-15万元", "15-50万元", "50万元以上"]),
    ("这笔投资占总资产的比例", ["超过50%", "25%-50%", "10%-25%", "10%以下"]),
    ("您的投资经验", ["没有经验", "1年以内", "1-3年", "3年以上"]),
    ("您对'最大回撤'的理解", ["没听过", "大概知道什么意思", "能用自己的话解释", "会用它评估策略风险"]),
    ("您的投资期限", ["3个月以内", "6个月到1年", "1-3年", "3年以上"]),
    ("10万一个月跌到8.5万，您会", ["全部卖出止损", "卖出一部分", "继续持有等回本", "分析后决定是否加仓"]),
    ("您更看重什么", ["本金绝对不能亏损", "小幅波动，略高于存款", "接受明显波动，追求较高收益", "接受大幅波动，追求高收益"]),
]


def get_risk_level(score):
    if score <= 14: return "保守型", "🔵"
    elif score <= 20: return "稳健型", "🟢"
    elif score <= 26: return "平衡型", "🟡"
    return "进取型", "🔴"


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
            st.caption("8道选择题，1分钟完成。判断您的风险承受能力，确保策略推荐不是盲目的。")
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
    st.caption("8道选择题，做完自动出结果。参考了证监会《证券期货投资者适当性管理办法》")

    scores = []
    for i, (q, options) in enumerate(RISK_QUESTIONS):
        st.markdown(f"**{i+1}. {q}**")
        ans = st.radio("", options, key=f"q{i}", index=None, label_visibility="collapsed")
        if ans:
            scores.append(options.index(ans) + 1)

    st.divider()

    if len(scores) == 8:
        total = sum(scores)
        level, emoji = get_risk_level(total)
        level_desc = {
            "保守型": "本金安全第一，几乎不能接受亏损",
            "稳健型": "能接受小幅波动，追求稳定增值",
            "平衡型": "能接受明显波动，追求较高收益",
            "进取型": "能接受大幅波动，追求高收益",
        }
        with st.container(border=True):
            st.success(f"### {emoji} {level}（{total}/32分）")
            st.caption(f"您的投资画像：{level_desc.get(level, '')}")

        st.session_state['risk_level'] = level
        st.session_state['risk_score'] = total

        st.info("💡 接下来，系统将根据您的风险等级，匹配最适合的量化策略，并展示真实的历史回测数据供您参考。")
        if st.button("🎯 查看AI策略推荐", type="primary", width='stretch'):
            go_to_page(2)
    else:
        st.info(f"已完成 {len(scores)}/8 题，请继续...")


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
        if demo_r is not None:
            summary = "\n".join([
                f"{n}：年化{r['annual_return']:+.2f}%，最大回撤{r['max_drawdown']:.2f}%"
                for n, r in demo_r.items()
            ])
            llm_reason = recommend_strategy(level, amount, horizon,
                ' + '.join(strategies), summary,
                st.session_state.get('risk_score'))
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
                    st.metric("最大回撤", f"{r['max_drawdown']:.2f}%",
                              delta=f"10万最多亏{amt_loss:,}元", delta_color="off")
                    st.caption(f"夏普: {r['sharpe_ratio']:.3f} | 胜率: {r['win_rate']:.1f}%")
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
    st.caption("三个策略对40只股票的最新评分排名。分段展示：推荐 / 观望 / 回避")

    signals_df = load_latest_signals()
    if not signals_df.empty:
        strategy_cols = [
            ("📊 策略A · 多因子综合", "signal_A"),
            ("📈 策略B · 趋势动量", "signal_B"),
            ("🔄 策略C · 均值回复", "signal_C"),
        ]
        tabs = st.tabs([s[0] for s in strategy_cols])

        for tab, (title, col) in zip(tabs, strategy_cols):
            with tab:
                ranked = signals_df[["name", "code", col]].sort_values(col, ascending=False)
                ranked.columns = ["股票名称", "代码", "评分"]

                if col == "signal_A":
                    hi, mid = 60, 45
                    lab_hi, lab_mid, lab_lo = "优秀推荐", "中等观望", "暂不推荐"
                elif col == "signal_C":
                    hi, mid = 55, 35
                    lab_hi, lab_mid, lab_lo = "超卖反弹信号", "一般（未到超卖区）", "回避"
                else:
                    hi, mid = 60, 40
                    lab_hi, lab_mid, lab_lo = "买入信号", "一般（观望）", "回避"

                good = ranked[ranked["评分"] >= hi]
                normal = ranked[(ranked["评分"] >= mid) & (ranked["评分"] < hi)]
                bad = ranked[ranked["评分"] < mid]

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.success(f"🟢 {lab_hi}（≥{hi}）")
                    if len(good) > 0:
                        centered_dataframe(good, hide_index=True, width='stretch')
                        st.caption(f"{len(good)} 只")
                    else:
                        st.caption("暂无")
                with c2:
                    st.info(f"🟡 {lab_mid}（{mid}-{hi-1}）")
                    if len(normal) > 0:
                        centered_dataframe(normal, hide_index=True, width='stretch')
                        st.caption(f"{len(normal)} 只")
                    else:
                        st.caption("暂无")
                with c3:
                    st.error(f"🔴 {lab_lo}（<{mid}）")
                    if len(bad) > 0:
                        centered_dataframe(bad, hide_index=True, width='stretch')
                        st.caption(f"{len(bad)} 只")
                    else:
                        st.caption("暂无")
    else:
        st.warning("暂无信号数据，请先运行 data/compute_signals.py")

    st.divider()
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
            centered_dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)

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
