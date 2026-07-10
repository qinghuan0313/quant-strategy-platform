import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
data = ak.stock_zh_index_daily(symbol="sh000905")
data["date"] = pd.to_datetime(data["date"])
data = data.set_index("date")
data = data.sort_index()
data["ma10"] = data["close"].rolling(10).mean()
data["ma30"] = data["close"].rolling(30).mean()
data["signal"] = 0
data.loc[data["ma10"]>data["ma30"],"signal"] = 1
data.loc[data["ma10"]<data["ma30"],"signal"] = 0
data["trade"] = data["signal"].diff()
data["return_market"] = data["close"].pct_change()
data["return_strategy"] = data["signal"].shift(1) * data["return_market"] 
data["nav_buy_hold"] = (1 + data["return_market"]).cumprod()
data["nav_strategy"] = (1 + data["return_strategy"]).cumprod()
days = len(data)
yearly_bh = data["nav_buy_hold"].iloc[-1]**(252/days)-1
yearly_st = data["nav_strategy"].iloc[-1]**(252/days)-1
win_rate = (data["return_strategy"] > 0).sum() / (data["return_strategy"] != 0).sum()
def max_drawdown(nav):
    peak = nav.cummax()              # 到每天为止的最高净值
    drawdown = (nav - peak) / peak    # 当前相比最高点跌了多少（负数）
    return drawdown.min()             # 取最惨的那天
maxdd_bh = max_drawdown(data["nav_buy_hold"])
maxdd_st = max_drawdown(data["nav_strategy"])
sharpe_bh = data["return_market"].mean() / data["return_market"].std() * (252 ** 0.5)
sharpe_st = data["return_strategy"].mean() / data["return_strategy"].std() * (252 ** 0.5)
print(f"回测结果（{data.index[0].date()} ~ {data.index[-1].date()}）")
print(f"{'='*40}")
print(f"{'指标':<12} {'买入持有':>10} {'双均线策略':>10}")
print(f"{'-'*35}")
print(f"{'年化收益':<10} {yearly_bh:>10.2%} {yearly_st:>10.2%}")
print(f"{'最大回撤':<10} {maxdd_bh:>10.2%} {maxdd_st:>10.2%}")
print(f"{'夏普比率':<10} {sharpe_bh:>10.2f} {sharpe_st:>10.2f}")
print(f"{'胜率':<12} {'-':>10} {win_rate:>10.2%}")
fig, axes = plt.subplots(3, 1, figsize=(14, 12))
ax1 = axes[0]
ax2 = axes[1]
ax3 = axes[2]
ax1.plot(data.index, data["close"], linewidth=0.6, alpha=0.6, label="收盘价")
ax1.plot(data.index, data["ma10"], linewidth=1, label="MA10 (10日均线)")
ax1.plot(data.index, data["ma30"], linewidth=1, label="MA30 (30日均线)")
buy_points = data[(data["trade"] == 1) & (data["signal"] == 1)]
sell_points = data[(data["trade"] == -1) & (data["signal"] == 0)]
ax1.scatter(buy_points.index, buy_points["close"], color="red", s=20, marker="^", label="买入", zorder=5)
ax1.scatter(sell_points.index, sell_points["close"], color="green", s=20, marker="v", label="卖出", zorder=5)
ax1.set_title("中证500 + 双均线 + 买卖点", fontsize=14)
ax1.legend(loc="upper left", fontsize=8)
ax1.grid(True, alpha=0.3)
ax2.plot(data.index, data["nav_buy_hold"], linewidth=1, label="买入持有")
ax2.plot(data.index, data["nav_strategy"], linewidth=1, label="双均线策略")
ax2.axhline(y=1, color="gray", linestyle="--", linewidth=0.5)  # y=1 基准线
ax2.set_title("净值曲线对比（1元起步）", fontsize=14)
ax2.legend(loc="upper left")
ax2.grid(True, alpha=0.3)
dd_bh = (data["nav_buy_hold"] - data["nav_buy_hold"].cummax()) / data["nav_buy_hold"].cummax()
dd_st = (data["nav_strategy"] - data["nav_strategy"].cummax()) / data["nav_strategy"].cummax()
ax3.fill_between(data.index, 0, dd_bh, alpha=0.3, label="买入持有回撤")
ax3.fill_between(data.index, 0, dd_st, alpha=0.3, label="策略回撤")
ax3.set_title("回撤曲线（越低越好）", fontsize=14)
ax3.legend(loc="lower left")
ax3.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
