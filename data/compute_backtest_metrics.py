# -*- coding: utf-8 -*-
"""预计算40只股票×3策略的回测指标，供信号表格使用"""
import sys; sys.path.insert(0, '.')
import pandas as pd
from strategies.strategy_a import strategy_multi_factor
from strategies.strategy_b import strategy_trend_momentum
from strategies.strategy_c import strategy_mean_reversion
from engine.backtest import run_backtest

def compute_all():
    stocks = pd.read_csv("data/stock_list.csv", dtype={'code': str})
    stocks['code'] = stocks['code'].str.zfill(6)

    strategies = [
        ("A", strategy_multi_factor),
        ("B", strategy_trend_momentum),
        ("C", strategy_mean_reversion),
    ]

    rows = []
    total = len(stocks) * len(strategies)
    count = 0

    for _, row in stocks.iterrows():
        code, name = row['code'], row['name']
        path = f"data/prices/{code}.csv"
        try:
            data = pd.read_csv(path, parse_dates=['date'])
            if len(data) < 200:
                continue
            for s_name, func in strategies:
                r = run_backtest(func, data.copy())
                rows.append({
                    "code": code, "name": name,
                    "strategy": s_name,
                    "annual_return": r['annual_return'],
                    "max_drawdown": r['max_drawdown'],
                    "sharpe_ratio": r['sharpe_ratio'],
                    "win_rate": r['win_rate'],
                    "trade_count": r['trade_count'],
                })
                count += 1
                print(f"[{count}/{total}] {s_name} {name} "
                      f"{r['annual_return']:+.1f}% dd={r['max_drawdown']:.1f}%")
        except Exception as e:
            print(f"X {code} {name}: {str(e)[:50]}")

    pd.DataFrame(rows).to_csv("data/backtest_metrics.csv", index=False)
    print(f"\nDone: {count} records saved")

if __name__ == "__main__":
    compute_all()
