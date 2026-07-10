# -*- coding: utf-8 -*-
"""预计算所有股票在三个策略上的最新评分，存CSV"""
import sys; sys.path.insert(0, '.')
import pandas as pd
from strategies.strategy_a import strategy_multi_factor
from strategies.strategy_b import strategy_trend_momentum
from strategies.strategy_c import strategy_mean_reversion

stock_df = pd.read_csv("data/stock_list.csv", dtype={'code': str})
stock_df['code'] = stock_df['code'].str.zfill(6)
strategies = {
    "A": strategy_multi_factor,
    "B": strategy_trend_momentum,
    "C": strategy_mean_reversion,
}

rows = []
for _, row in stock_df.iterrows():
    code, name = row['code'], row['name']
    path = f"data/prices/{str(code).zfill(6)}.csv"
    try:
        data = pd.read_csv(path, parse_dates=['date'])
        r = {"code": code, "name": name}
        for s_name, s_func in strategies.items():
            df = s_func(data.copy())
            r[f"signal_{s_name}"] = df['signal'].iloc[-1]
        rows.append(r)
        print(f"OK {code} {name}")
    except Exception as e:
        print(f"X  {code} {name}  {str(e)[:40]}  (用默认50)")
        r = {"code": code, "name": name,
             "signal_A": 50.0, "signal_B": 50.0, "signal_C": 50.0}
        rows.append(r)

pd.DataFrame(rows).to_csv("data/latest_signals.csv", index=False)
print(f"\nDone. {len(rows)} stocks saved to data/latest_signals.csv")
