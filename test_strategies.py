# -*- coding: utf-8 -*-
"""
一次性测试所有策略，用真实数据回测并对比
"""

import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import baostock as bs
import warnings
warnings.filterwarnings('ignore')

from strategies.strategy_a import strategy_multi_factor
from strategies.strategy_b import strategy_trend_momentum
from strategies.strategy_c import strategy_mean_reversion
from engine.backtest import run_backtest

# ====================== 配置 ======================
STOCKS = {
    "sh.600900": "长江电力",
    "sh.600519": "贵州茅台",
    "sz.300750": "宁德时代",
    "sh.600036": "招商银行",
    "sz.000858": "五粮液",
    "sz.002714": "牧原股份",
    "sh.601318": "中国平安",
    "sz.000333": "美的集团",
    "sh.601088": "中国神华",
    "sh.600030": "中信证券",
}

TEST_STOCKS = ["sh.600900", "sh.600519", "sz.300750", "sh.600036", "sz.000858"]
START_DATE = "2023-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")


def fetch_data(code):
    """用baostock拉取单只股票数据"""
    rs = bs.query_history_k_data_plus(
        code, "date,open,high,low,close,volume",
        start_date=START_DATE, end_date=END_DATE,
        frequency="d", adjustflag="2"
    )
    data_list = []
    while (rs.error_code == '0') & rs.next():
        data_list.append(rs.get_row_data())

    if not data_list:
        return None

    df = pd.DataFrame(data_list, columns=rs.fields)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    return df


def main():
    print("=" * 60)
    print("策略回测对比测试")
    print(f"回测区间: {START_DATE} → {END_DATE}")
    print("=" * 60)

    # 登录baostock
    bs.login()

    all_results = {}

    for code in TEST_STOCKS:
        name = STOCKS[code]
        symbol = code.split('.')[1]  # sh.600900 → 600900

        print(f"\n{'─' * 60}")
        print(f"测试: {name} ({symbol})")
        print(f"{'─' * 60}")

        # 拉数据
        data = fetch_data(code)
        if data is None or len(data) < 120:
            print("  数据不足，跳过")
            continue
        print(f"  获取成功，{len(data)}条记录")

        results = {}

        # 策略A
        print("  策略A（多因子）...")
        res_a = run_backtest(strategy_multi_factor, data)
        results['A-多因子'] = res_a
        print(f"    年化收益: {res_a['annual_return']:+.2f}%, "
              f"最大回撤: {res_a['max_drawdown']:.2f}%, "
              f"夏普: {res_a['sharpe_ratio']:.3f}, "
              f"交易: {res_a['trade_count']}次")

        # 策略B
        print("  策略B（趋势动量）...")
        res_b = run_backtest(strategy_trend_momentum, data)
        results['B-趋势动量'] = res_b
        print(f"    年化收益: {res_b['annual_return']:+.2f}%, "
              f"最大回撤: {res_b['max_drawdown']:.2f}%, "
              f"夏普: {res_b['sharpe_ratio']:.3f}, "
              f"交易: {res_b['trade_count']}次")

        # 策略C
        print("  策略C（均值回复）...")
        res_c = run_backtest(strategy_mean_reversion, data)
        results['C-均值回复'] = res_c
        print(f"    年化收益: {res_c['annual_return']:+.2f}%, "
              f"最大回撤: {res_c['max_drawdown']:.2f}%, "
              f"夏普: {res_c['sharpe_ratio']:.3f}, "
              f"交易: {res_c['trade_count']}次")

        all_results[name] = results

    # 登出
    bs.logout()

    # ======== 汇总对比表 ========
    print(f"\n{'=' * 70}")
    print("策略对比汇总")
    print("=" * 70)

    for stock_name, results in all_results.items():
        print(f"\n【{stock_name}】")
        header = f"{'策略':<14} {'年化收益':>9} {'最大回撤':>9} {'夏普':>8} {'胜率':>7} {'交易':>5}"
        print(header)
        print("-" * 55)
        for s_name, r in results.items():
            print(f"{s_name:<14} {r['annual_return']:>+8.2f}% "
                  f"{r['max_drawdown']:>8.2f}% {r['sharpe_ratio']:>7.3f} "
                  f"{r['win_rate']:>6.2f}% {r['trade_count']:>4}次")


if __name__ == "__main__":
    main()
