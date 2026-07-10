"""
第二步：双均线交叉策略 + 回测
短期均线上穿长期均线 → 买入
短期均线下穿长期均线 → 卖出
"""
import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt

# ---- 中文显示 ----
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

# ============================================
# 1. 拉数据
# ============================================
print("拉取数据...")
data = ak.stock_zh_index_daily(symbol="sh000300")
data["date"] = pd.to_datetime(data["date"])
data = data.set_index("date").sort_index()
data = data[data.index >= "2020-01-01"]  # 只看2020年以后

# ============================================
# 2. 算两条均线
# ============================================
# rolling(n) 的意思是"往前看 n 天的数据"，
# .mean() 对这 n 天取平均值 → 就是均线
data["ma5"]  = data["close"].rolling(5).mean()   # 5日均线，短期
data["ma20"] = data["close"].rolling(20).mean()  # 20日均线，长期

# ============================================
# 3. 生成交易信号
# ============================================
# 金叉：昨天 ma5 < ma20，今天 ma5 > ma20 → 买入信号 = 1
# 死叉：昨天 ma5 > ma20，今天 ma5 < ma20 → 卖出信号 = -1
data["signal"] = 0
data.loc[data["ma5"] > data["ma20"], "signal"] = 1   # 持仓状态
data.loc[data["ma5"] < data["ma20"], "signal"] = 0   # 空仓状态

# 持仓变化：今天和昨天不一样的地方 → 发生了交易
data["trade"] = data["signal"].diff()  # diff() = 今天减昨天，变化的地方不为0

# ============================================
# 4. 算策略收益
# ============================================
# 持仓的时候拿市场收益，空仓的时候收益为0
data["return_market"] = data["close"].pct_change()        # 市场每天的收益率
data["return_strategy"] = data["signal"].shift(1) * data["return_market"]
# shift(1) = 用昨天的信号决定今天的仓位（今天收盘后才能看到今天的信号，不能作弊）

# 累计收益：从1块钱开始，每天 (1 + 收益率) 连乘
data["nav_buy_hold"] = (1 + data["return_market"]).cumprod()   # 买入持有
data["nav_strategy"] = (1 + data["return_strategy"]).cumprod()  # 策略净值

# ============================================
# 5. 计算评价指标
# ============================================
# 年化收益率
days = len(data)
yearly_return_bh = data["nav_buy_hold"].iloc[-1] ** (252 / days) - 1
yearly_return_st = data["nav_strategy"].iloc[-1] ** (252 / days) - 1

# 最大回撤：从最高点跌到最低点的最大幅度
def max_drawdown(nav):
    peak = nav.cummax()           # 到每天为止的最高净值
    drawdown = (nav - peak) / peak # 当前相比最高点跌了多少
    return drawdown.min()          # 取最惨的那天

maxdd_bh = max_drawdown(data["nav_buy_hold"])
maxdd_st = max_drawdown(data["nav_strategy"])

# 夏普比率 = 平均收益 / 收益波动 = 每承担一份风险赚了多少
sharpe_bh = data["return_market"].mean() / data["return_market"].std() * (252 ** 0.5)
sharpe_st = data["return_strategy"].mean() / data["return_strategy"].std() * (252 ** 0.5)

# 胜率：交易赚钱的次数占比
trades = data[data["trade"] != 0].copy()  # 只挑出发生交易的日子
# 简化计算：看策略每日收益为正的比例
win_rate = (data["return_strategy"] > 0).sum() / (data["return_strategy"] != 0).sum()

print(f"\n{'='*40}")
print(f"回测结果（{data.index[0].date()} ~ {data.index[-1].date()}）")
print(f"{'='*40}")
print(f"{'指标':<12} {'买入持有':>10} {'双均线策略':>10}")
print(f"{'-'*35}")
print(f"{'年化收益':<10} {yearly_return_bh:>10.2%} {yearly_return_st:>10.2%}")
print(f"{'最大回撤':<10} {maxdd_bh:>10.2%} {maxdd_st:>10.2%}")
print(f"{'夏普比率':<10} {sharpe_bh:>10.2f} {sharpe_st:>10.2f}")
print(f"{'胜率':<12} {'-':>10} {win_rate:>10.2%}")

# ============================================
# 6. 画图
# ============================================
fig, axes = plt.subplots(3, 1, figsize=(14, 12))

# 图1：收盘价 + 均线
ax1 = axes[0]
ax1.plot(data.index, data["close"], linewidth=0.6, alpha=0.6, label="收盘价")
ax1.plot(data.index, data["ma5"], linewidth=1, label="MA5 (5日均线)")
ax1.plot(data.index, data["ma20"], linewidth=1, label="MA20 (20日均线)")
# 标出金叉买入点
buy_points = data[(data["trade"] == 1) & (data["signal"] == 1)]
sell_points = data[(data["trade"] == -1) & (data["signal"] == 0)]
ax1.scatter(buy_points.index, buy_points["close"], color="red", s=20, marker="^", label="买入", zorder=5)
ax1.scatter(sell_points.index, sell_points["close"], color="green", s=20, marker="v", label="卖出", zorder=5)
ax1.set_title("沪深300 + 双均线 + 买卖点", fontsize=14)
ax1.legend(loc="upper left", fontsize=8)
ax1.grid(True, alpha=0.3)

# 图2：净值曲线对比
ax2 = axes[1]
ax2.plot(data.index, data["nav_buy_hold"], linewidth=1, label="买入持有")
ax2.plot(data.index, data["nav_strategy"], linewidth=1, label="双均线策略")
ax2.axhline(y=1, color="gray", linestyle="--", linewidth=0.5)
ax2.set_title("净值曲线对比（1元起步）", fontsize=14)
ax2.legend(loc="upper left")
ax2.grid(True, alpha=0.3)

# 图3：回撤曲线
ax3 = axes[2]
dd_bh = (data["nav_buy_hold"] - data["nav_buy_hold"].cummax()) / data["nav_buy_hold"].cummax()
dd_st = (data["nav_strategy"] - data["nav_strategy"].cummax()) / data["nav_strategy"].cummax()
ax3.fill_between(data.index, 0, dd_bh, alpha=0.3, label="买入持有回撤")
ax3.fill_between(data.index, 0, dd_st, alpha=0.3, label="策略回撤")
ax3.set_title("回撤曲线（越低越好）", fontsize=14)
ax3.legend(loc="lower left")
ax3.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
print("\n完成！")
