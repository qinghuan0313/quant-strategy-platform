# -*- coding: utf-8 -*-
"""统一回测引擎 + 绩效指标"""

import pandas as pd
import numpy as np


def sharpe_ratio(returns, risk_free=0.03):
    """年化夏普比率"""
    if len(returns) == 0 or returns.std() == 0:
        return 0
    excess = returns - risk_free / 252
    return (excess.mean() / returns.std()) * np.sqrt(252)


def max_drawdown(equity):
    """最大回撤（百分比）"""
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return dd.min() * 100


def annual_return(equity, days):
    """年化收益率（百分比）"""
    if days <= 0 or equity.iloc[0] <= 0:
        return 0
    total_return = equity.iloc[-1] / equity.iloc[0]
    return (total_return ** (252 / days) - 1) * 100


def win_rate(returns):
    """日胜率（百分比）"""
    if len(returns) == 0:
        return 0
    return (returns > 0).sum() / len(returns) * 100


def calmar_ratio(annual_ret, max_dd):
    """Calmar比率 = 年化收益 / 最大回撤"""
    if max_dd == 0:
        return 0
    return annual_ret / abs(max_dd)


def run_backtest(strategy_func, data, init_capital=100000, commission=0.0003, **params):
    """
    统一回测引擎

    参数：
        strategy_func: 策略函数，输入DataFrame → 输出带signal列的DataFrame
        data: 行情数据，必须包含 date, open, close
        init_capital: 初始资金
        commission: 手续费率（默认万三）
        **params: 传给策略函数的参数

    返回：
        dict: 包含各项绩效指标和净值序列
    """
    # 运行策略
    df = strategy_func(data.copy(), **params)

    # 将signal转为持仓权重
    # >60 满仓(1.0) | 55-60 半仓(0.5) | 45-55 保持 | 40-45 半仓(0.5) | <40 空仓(0)
    df['position'] = 0.0
    df.loc[df['signal'] > 60, 'position'] = 1.0
    df.loc[(df['signal'] > 55) & (df['signal'] <= 60), 'position'] = 0.5
    df.loc[(df['signal'] >= 40) & (df['signal'] <= 45), 'position'] = 0.5
    # 45-55保持：先填0再ffill
    df['position'] = df['position'].replace(0.0, np.nan).ffill().fillna(0.0)

    # 计算每日收益率
    df['return'] = df['close'].pct_change()
    df['strategy_return'] = df['position'].shift(1) * df['return']
    df['strategy_return'] = df['strategy_return'].fillna(0)

    # 扣除手续费（调仓日）
    df['trade'] = df['position'].diff().abs()
    df['strategy_return'] = df['strategy_return'] - df['trade'] * commission

    # 计算净值
    df['strategy_return'] = df['strategy_return'].fillna(0)
    df['equity'] = (1 + df['strategy_return']).cumprod() * init_capital

    # 绩效统计
    days = len(df)
    ann_ret = annual_return(df['equity'], days)
    max_dd_val = max_drawdown(df['equity'])
    sharpe = sharpe_ratio(df['strategy_return'])
    win = win_rate(df['strategy_return'])
    calmar = calmar_ratio(ann_ret, max_dd_val)
    total_ret = (df['equity'].iloc[-1] / init_capital - 1) * 100

    return {
        'total_return': round(total_ret, 2),
        'annual_return': round(ann_ret, 2),
        'max_drawdown': round(max_dd_val, 2),
        'sharpe_ratio': round(sharpe, 3),
        'win_rate': round(win, 2),
        'calmar_ratio': round(calmar, 3),
        'trade_count': int(df['trade'].sum()),
        'equity_curve': df[['date', 'equity', 'signal', 'position']]
    }
