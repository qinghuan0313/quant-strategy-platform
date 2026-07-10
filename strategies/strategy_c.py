# -*- coding: utf-8 -*-
"""
策略C：均值回复复合
核心逻辑：判断股票是否"跌过头了"——四个维度交叉验证后才入场
四个子信号加权：
  1. RSI极端超卖（30%）：RSI越低反弹概率越高
  2. 布林带偏离度（25%）：价格偏离下轨多远
  3. 下跌衰竭反转（25%）：跌势是否已耗尽
  4. 恐慌放量底（20%）：恐慌抛售是否到极限
"""

import pandas as pd
import numpy as np


def calc_rsi_at(df, idx, period=14):
    """计算单日RSI"""
    if idx < period:
        return 50
    prices = df['close'].iloc[idx - period:idx + 1].values
    gains = []
    losses = []
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-diff)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def strategy_mean_reversion(data, **params):
    """
    策略C：均值回复复合

    参数：
        data: DataFrame，必须包含 date, open, close, high, low, volume
        params: 可覆盖默认参数

    返回：
        DataFrame，添加 signal 列（0-100评分）
    """
    rsi_period = params.get('rsi_period', 14)
    bb_period = params.get('bb_period', 20)
    bb_std = params.get('bb_std', 2.0)

    df = data.copy()
    df['signal'] = 50.0

    # 预计算
    df['ma20'] = df['close'].rolling(bb_period).mean()
    df['std20'] = df['close'].rolling(bb_period).std()
    df['vol_ma5'] = df['volume'].rolling(5).mean()

    for idx in range(len(df)):
        # ======== 信号1：RSI极端程度（权重30%） ========
        rsi_val = calc_rsi_at(df, idx, rsi_period)

        if rsi_val < 15:
            rsi_score = 90   # 极度超卖，反弹
        elif rsi_val < 20:
            rsi_score = 75 + (20 - rsi_val) * 3   # 20→75, 15→90
        elif rsi_val < 30:
            rsi_score = 55 + (30 - rsi_val) * 2   # 30→55, 20→75
        elif rsi_val < 40:
            rsi_score = 50 + (40 - rsi_val) * 0.5  # 40→50, 30→55
        elif rsi_val > 75:
            rsi_score = 15   # 严重超买，均值回复策略坚决不做多
        elif rsi_val > 65:
            rsi_score = 30   # 超买区域
        elif rsi_val > 55:
            rsi_score = 40   # 偏贵
        else:
            rsi_score = 50   # 中性

        # ======== 信号2：布林带偏离度（权重25%） ========
        if idx >= bb_period and pd.notna(df['std20'].iloc[idx]) and df['std20'].iloc[idx] > 0:
            ma20 = df['ma20'].iloc[idx]
            std20 = df['std20'].iloc[idx]
            price = df['close'].iloc[idx]

            bb_lower = ma20 - bb_std * std20
            bb_bottom = ma20 - 2.5 * std20
            bb_upper = ma20 + bb_std * std20

            if price < bb_bottom:
                bb_score = 90   # 极端偏离，强反弹信号
            elif price < bb_lower:
                deviation = (bb_lower - price) / std20
                bb_score = 60 + deviation * 15  # 偏离越多分越高
            elif price < ma20 - std20:
                bb_score = 58   # 温和偏离下轨
            elif price > bb_upper:
                bb_score = 15   # 上轨之上，不做多
            elif price > ma20 + std20:
                bb_score = 35
            elif price > ma20:
                bb_score = 40   # 价格在均线上方，不适合抄底
            else:
                bb_score = 50
            bb_score = max(0, min(100, bb_score))
        else:
            bb_score = 50

        # ======== 信号3：下跌衰竭反转（权重25%） ========
        if idx >= 4:
            c0 = df['close'].iloc[idx]
            c1 = df['close'].iloc[idx - 1]
            c2 = df['close'].iloc[idx - 2]
            c3 = df['close'].iloc[idx - 3]
            c4 = df['close'].iloc[idx - 4] if idx >= 4 else c3

            o0 = df['open'].iloc[idx]
            l0 = df['low'].iloc[idx]
            v0 = df['volume'].iloc[idx]

            # 情况1：连续下跌后收阳（最佳信号）
            if c3 > c2 > c1 and c0 > c1:
                reversal_score = 85
            # 情况2：前两日下跌，今日收阳
            elif c2 > c1 and c0 > c1:
                reversal_score = 72
            # 情况3：探底回升（下影线长 + 收阳）
            elif c0 > o0 and (l0 < c1) and (c0 - l0) > (c0 - o0) * 2:
                reversal_score = 68
            # 情况4：今日收阳（单纯阳线）
            elif c0 > c1:
                reversal_score = 55
            # 情况5：继续下跌但跌幅缩小
            elif c0 < c1 and c1 < c2:
                if abs(c0 - c1) < abs(c1 - c2):
                    reversal_score = 50  # 跌速放缓，可能快见底
                else:
                    reversal_score = 30  # 加速下跌，不能抄
            else:
                reversal_score = 25  # 继续下跌，无反转迹象

            # 成交量辅助：反转日成交量萎缩 = 卖压耗尽
            if reversal_score >= 55 and idx >= 5 and pd.notna(df['vol_ma5'].iloc[idx]):
                if v0 < df['vol_ma5'].iloc[idx] * 0.7:
                    reversal_score += 8  # 缩量止跌，更可靠
        else:
            reversal_score = 50

        # ======== 信号4：恐慌放量底（权重20%） ========
        if idx >= 5 and pd.notna(df['vol_ma5'].iloc[idx]):
            vol_now = df['volume'].iloc[idx]
            vol_ma5 = df['vol_ma5'].iloc[idx]

            if idx >= 3:
                chg_3d = (df['close'].iloc[idx] - df['close'].iloc[idx - 3]) / df['close'].iloc[idx - 3]
            else:
                chg_3d = 0

            vol_ratio = vol_now / vol_ma5 if vol_ma5 > 0 else 1

            if vol_ratio > 2.0 and chg_3d < -0.08:
                panic_score = 90   # 暴跌+巨量=恐慌极限，反弹在即
            elif vol_ratio > 1.5 and chg_3d < -0.05:
                panic_score = 75   # 恐慌抛售
            elif vol_ratio > 1.3 and chg_3d < -0.03:
                panic_score = 62   # 轻度恐慌
            elif vol_ratio < 0.5 and chg_3d < -0.02:
                panic_score = 68   # 缩量阴跌后，卖盘可能耗尽
            elif vol_ratio < 0.6 and chg_3d < 0:
                panic_score = 55   # 缩量下跌
            elif vol_ratio > 1.2 and chg_3d > 0.03:
                panic_score = 35   # 放量反弹，已错过最佳抄底点
            else:
                panic_score = 50
        else:
            panic_score = 50

        # ======== 加权综合 ========
        composite = (
            rsi_score * 0.30 +
            bb_score * 0.25 +
            reversal_score * 0.25 +
            panic_score * 0.20
        )

        df.loc[df.index[idx], 'signal'] = round(max(0, min(100, composite)), 1)

    # 清理临时列
    df.drop(columns=['ma20', 'std20', 'vol_ma5'], inplace=True, errors='ignore')
    return df
