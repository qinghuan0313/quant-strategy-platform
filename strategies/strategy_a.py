# -*- coding: utf-8 -*-
"""
策略A：多因子综合评分（队长原策略改造）
五个因子加权：
  资金流向(30%) / 市场情绪(20%) / 陷阱识别(20%) / 技术形态(20%) / K线顶底(10%)
"""

import pandas as pd
import numpy as np


# ===== 五个因子函数（从队长代码原样提取） =====

def calc_fund_flow(df, idx):
    """资金流向：成交量加权均价 vs 当前价"""
    if idx < 5:
        return 50
    vol = df["volume"].iloc[idx - 4:idx + 1].values
    price = df["close"].iloc[idx - 4:idx + 1].values
    vwap = np.average(price, weights=vol)
    current = df["close"].iloc[idx]
    strength = (current - vwap) / vwap * 100
    score = 50 + strength * 2
    return max(0, min(100, score))


def calc_sentiment(df, idx):
    """市场情绪：量价关系"""
    if idx < 10:
        return 50
    vol_ma5 = df["volume"].rolling(5).mean().iloc[idx]
    vol_ratio = df["volume"].iloc[idx] / vol_ma5 if vol_ma5 > 0 else 1
    price_change = (df["close"].iloc[idx] - df["close"].iloc[idx - 1]) / df["close"].iloc[idx - 1]
    if price_change > 0 and vol_ratio > 1.5:
        return 70
    elif price_change < 0 and vol_ratio > 1.5:
        return 30
    else:
        return 50


def calc_trap(df, idx):
    """陷阱识别：上影线、假突破"""
    if idx < 1:
        return 50
    row = df.iloc[idx]
    candle_range = row["high"] - row["low"]
    if candle_range > 0:
        shadow_ratio = (row["high"] - max(row["open"], row["close"])) / candle_range
        if shadow_ratio > 0.6:
            return 30
    if idx >= 5:
        high_5 = df["high"].iloc[idx - 5:idx].max()
        if row["high"] > high_5 and row["close"] < high_5:
            return 30
    return 50


def calc_technical(df, idx):
    """技术形态：均线排列 + 金叉死叉 + 趋势方向"""
    if idx < 20:
        return 50
    ma5 = df["close"].rolling(5).mean().iloc[idx]
    ma10 = df["close"].rolling(10).mean().iloc[idx]
    ma20 = df["close"].rolling(20).mean().iloc[idx]
    score = 50
    if ma5 > ma10 > ma20:
        score += 15
    elif ma5 > ma20:
        score += 8
    elif ma5 < ma20:
        score -= 10
    if idx >= 1:
        prev_ma5 = df["close"].rolling(5).mean().shift(1).iloc[idx]
        prev_ma20 = df["close"].rolling(20).mean().shift(1).iloc[idx]
        if prev_ma5 <= prev_ma20 and ma5 > ma20:
            score += 20
        elif prev_ma5 >= prev_ma20 and ma5 < ma20:
            score -= 20
    ma60 = df["close"].rolling(60).mean().iloc[idx] if idx >= 59 else df["close"].iloc[idx]
    if df["close"].iloc[idx] > ma60:
        score += 10
    else:
        score -= 5
    return max(0, min(100, score))


def calc_top_bottom(df, idx):
    """K线顶底：局部高低点识别"""
    if idx < 5 or idx > len(df) - 6:
        return 50
    high = df["high"].iloc[idx]
    low = df["low"].iloc[idx]
    if high > df["high"].iloc[idx - 2:idx].max() and high > df["high"].iloc[idx + 1:idx + 3].max():
        return 30  # 局部顶
    if low < df["low"].iloc[idx - 2:idx].min() and low < df["low"].iloc[idx + 1:idx + 3].min():
        return 70  # 局部底
    return 50


# ===== 统一接口 =====

def strategy_multi_factor(data, **params):
    """
    策略A：多因子综合评分

    参数：
        data: DataFrame，必须包含 date, open, close, high, low, volume
        params: 可覆盖默认权重

    返回：
        DataFrame，添加 signal 列（0-100评分）
    """
    w_fund = params.get('w_fund', 0.3)
    w_sent = params.get('w_sent', 0.2)
    w_trap = params.get('w_trap', 0.2)
    w_tech = params.get('w_tech', 0.2)
    w_tb = params.get('w_tb', 0.1)

    df = data.copy()
    df['signal'] = 50.0

    for idx in range(len(df)):
        fund = calc_fund_flow(df, idx)
        sent = calc_sentiment(df, idx)
        trap = calc_trap(df, idx)
        tech = calc_technical(df, idx)
        tb = calc_top_bottom(df, idx)

        total = fund * w_fund + sent * w_sent + trap * w_trap + tech * w_tech + tb * w_tb
        df.loc[df.index[idx], 'signal'] = round(max(0, min(100, total)), 1)

    return df
