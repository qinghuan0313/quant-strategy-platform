"""
第一步：拉取沪深300历史数据，计算日收益率，画图
使用 akshare 数据源（国内可用，不需要翻墙）
"""
import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt

# 解决中文显示问题 —— 告诉 matplotlib 用系统里的中文字体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]  # 微软雅黑
plt.rcParams["axes.unicode_minus"] = False             # 让负号正常显示

# 1. 拉数据 —— 从 AKShare 下载沪深300指数的历史日线数据
#    sh000300 是上证交易所的沪深300指数代码
print("正在拉取数据...")
data = ak.stock_zh_index_daily(symbol="sh000300")
print(f"拉到了 {len(data)} 天的数据")

# 2. 整理数据 —— 把日期设成索引，方便后面画图
data["date"] = pd.to_datetime(data["date"])
data = data.set_index("date")
data = data.sort_index()

# 只保留 2020 年之后的数据
data = data[data.index >= "2020-01-01"]

# 3. 算日收益率 —— 今天收盘价 / 昨天收盘价 - 1
data["return"] = data["close"].pct_change()

# 4. 画图 —— 两张图：收盘价走势 + 日收益率分布
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

# 上图：收盘价
ax1.plot(data.index, data["close"], linewidth=0.8)
ax1.set_title("沪深300指数 收盘价", fontsize=14)
ax1.set_ylabel("指数点数")
ax1.grid(True, alpha=0.3)

# 下图：日收益率
ax2.plot(data.index, data["return"], linewidth=0.5, alpha=0.7)
ax2.set_title("日收益率", fontsize=14)
ax2.set_ylabel("收益率")
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

print("完成！")
