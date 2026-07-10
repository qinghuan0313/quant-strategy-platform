import akshare as ak
import pandas as pd

data = ak.stock_zh_index_daily(symbol="sh000905")
data["date"] = pd.to_datetime(data['date'])
data = data.set_index("date")
data = data.sort_index()
data = data[data.index >= "2020-01-01"]
print(data.head(3))
print(f" 共{len(data)}天")

data["ma10"] = data["close"].rolling(10).mean()
data["ma30"] = data["close"].rolling(30).mean()
print(data[["close","ma10","ma30"]].head(11))

data["signal"] = 0
data.loc[data["ma10"] > data["ma30"],"signal"] = 1
data.loc[data["ma10"] < data["ma30"],"signal"] = 0
data["trade"] = data["signal"].diff()
print(data["signal"].value_counts())
print(data[data["trade"]==1][["close","ma10","ma30","signal"]].head(3))
