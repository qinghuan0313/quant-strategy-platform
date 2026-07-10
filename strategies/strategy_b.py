# -*- coding: utf-8 -*-
"""
策略B：趋势动量复合
核心逻辑：判断趋势质量——质量高就买，质量差就观望
四个子信号加权：
  1. 均线排列强度（30%）：MA5/10/20/60 多头排列程度
  2. ADX趋势强度（25%）：趋势是否存在、力度多大
  3. 价格通道位置（25%）：股价在20日通道中的位置
  4. 成交量确认（20%）：量价配合是否健康
"""

import pandas as pd
import numpy as np


def calc_adx(df, idx, period=14):
    """
    计算单日的ADX值
    ADX衡量趋势强度，0-100，>25表示趋势存在，<20表示震荡
    """
    if idx < period + 1:
        return 25  # 数据不足，返回中性值

    # 取最近 period+1 天的数据
    high = df['high'].iloc[idx - period:idx + 1].values
    low = df['low'].iloc[idx - period:idx + 1].values
    close = df['close'].iloc[idx - period:idx + 1].values

    tr_list = []
    plus_dm_list = []
    minus_dm_list = []

    for i in range(1, len(high)):
        # 真实波幅 TR
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1])
        )
        tr_list.append(tr)

        # +DM 和 -DM
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]

        if up > down and up > 0:
            plus_dm = up
        else:
            plus_dm = 0

        if down > up and down > 0:
            minus_dm = down
        else:
            minus_dm = 0

        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)

    # 使用Wilder平滑（等效于EMA with alpha=1/period）
    tr_smooth = tr_list[0]
    plus_dm_smooth = plus_dm_list[0]
    minus_dm_smooth = minus_dm_list[0]

    for i in range(1, len(tr_list)):
        tr_smooth = tr_smooth - tr_smooth / period + tr_list[i]
        plus_dm_smooth = plus_dm_smooth - plus_dm_smooth / period + plus_dm_list[i]
        minus_dm_smooth = minus_dm_smooth - minus_dm_smooth / period + minus_dm_list[i]

    # +DI 和 -DI
    plus_di = (plus_dm_smooth / tr_smooth) * 100 if tr_smooth > 0 else 0
    minus_di = (minus_dm_smooth / tr_smooth) * 100 if tr_smooth > 0 else 0

    # DX 和 ADX
    di_sum = plus_di + minus_di
    dx = (abs(plus_di - minus_di) / di_sum) * 100 if di_sum > 0 else 0

    # ADX = DX的period日平滑均值，这里返回单日DX作为近似
    # 精确ADX需要前period个DX的均值，为简化直接用当前DX
    adx = dx
    return adx


def calc_rsi(df, idx, period=14):
    """计算单日RSI"""
    if idx < period + 1:
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


def strategy_trend_momentum(data, **params):
    """
    策略B：趋势动量复合

    参数：
        data: DataFrame，必须包含 date, open, close, high, low, volume
        params: 可覆盖默认参数

    返回：
        DataFrame，添加 signal 列（0-100评分）
    """
    # 默认参数
    fast_ma = params.get('fast_ma', 5)
    mid_ma = params.get('mid_ma', 10)
    slow_ma = params.get('slow_ma', 20)
    trend_ma = params.get('trend_ma', 60)
    adx_period = params.get('adx_period', 14)
    channel_period = params.get('channel_period', 20)

    df = data.copy()
    df['signal'] = 50.0

    # 预计算均线
    df['ma5'] = df['close'].rolling(fast_ma).mean()
    df['ma10'] = df['close'].rolling(mid_ma).mean()
    df['ma20'] = df['close'].rolling(slow_ma).mean()
    df['ma60'] = df['close'].rolling(trend_ma).mean()
    df['vol_ma10'] = df['volume'].rolling(10).mean()

    for idx in range(len(df)):
        # ======== 信号1：均线排列强度（权重30%） ========
        if idx >= 60:
            price = df['close'].iloc[idx]
            mas = {
                'MA5': df['ma5'].iloc[idx],
                'MA10': df['ma10'].iloc[idx],
                'MA20': df['ma20'].iloc[idx],
                'MA60': df['ma60'].iloc[idx],
            }

            # 价格站上几条均线
            above_count = sum(1 for ma in mas.values() if pd.notna(ma) and price > ma)
            # 4条全上=80分，全下=20分
            ma_score_base = above_count * 15 + 20

            # 均线是否多头排列
            ma_values = [v for v in mas.values() if pd.notna(v)]
            aligned = 0
            for j in range(len(ma_values) - 1):
                if ma_values[j] > ma_values[j + 1]:
                    aligned += 1
            # 4线全多头额外+20，3线+15，以此类推
            alignment_bonus = aligned * 5

            ma_score = min(100, ma_score_base + alignment_bonus)

            # 价格偏离MA60的程度（偏离太多=趋势过热）
            if pd.notna(mas['MA60']) and mas['MA60'] > 0:
                deviation = (price - mas['MA60']) / mas['MA60'] * 100
                if deviation > 30:
                    ma_score -= 15  # 偏离过大，追高风险
                elif deviation > 20:
                    ma_score -= 8
        else:
            ma_score = 50

        # ======== 信号2：ADX趋势强度（权重25%） ========
        if idx >= adx_period + 1:
            adx_val = calc_adx(df, idx, adx_period)
            if adx_val > 40:
                adx_score = 85   # 强趋势，放心参与
            elif adx_val > 30:
                adx_score = 65 + (adx_val - 30) * 1.5  # 30→65, 40→80
            elif adx_val > 25:
                adx_score = 55 + (adx_val - 25) * 2.0  # 25→55, 30→65
            elif adx_val > 20:
                adx_score = 50   # 中性
            else:
                adx_score = 35   # 震荡市，趋势策略回避
        else:
            adx_score = 50

        # ======== 信号3：价格通道位置（权重25%） ========
        if idx >= channel_period:
            high_n = df['high'].iloc[idx - channel_period + 1:idx + 1].max()
            low_n = df['low'].iloc[idx - channel_period + 1:idx + 1].min()
            channel_range = high_n - low_n

            if channel_range > 0:
                position = (df['close'].iloc[idx] - low_n) / channel_range

                if 0.4 <= position <= 0.7:
                    channel_score = 80   # 通道中上段，趋势确认但未过热
                elif 0.7 < position <= 0.85:
                    channel_score = 65   # 偏高但还可接受
                elif position > 0.90:
                    channel_score = 35   # 通道顶部，追高风险极大
                elif position < 0.20:
                    channel_score = 30   # 通道底部，趋势可能已反转
                elif 0.20 <= position < 0.40:
                    channel_score = 55   # 偏低位，等确认
                else:
                    channel_score = 50
            else:
                channel_score = 50
        else:
            channel_score = 50

        # ======== 信号4：成交量确认（权重20%） ========
        if idx >= 10 and pd.notna(df['vol_ma10'].iloc[idx]):
            cur_vol = df['volume'].iloc[idx]
            vol_ma = df['vol_ma10'].iloc[idx]

            if idx >= 1:
                price_chg = df['close'].iloc[idx] - df['close'].iloc[idx - 1]
            else:
                price_chg = 0

            vol_ratio = cur_vol / vol_ma if vol_ma > 0 else 1

            if price_chg > 0 and vol_ratio > 1.2:
                vol_score = 85   # 放量上涨，趋势健康
            elif price_chg > 0 and vol_ratio > 0.8:
                vol_score = 65   # 温和上涨
            elif price_chg > 0 and vol_ratio < 0.6:
                vol_score = 40   # 无量上涨，趋势乏力
            elif price_chg < 0 and vol_ratio < 0.8:
                vol_score = 60   # 缩量回调，正常调整
            elif price_chg < 0 and vol_ratio > 1.5:
                vol_score = 25   # 放量下跌，趋势危险
            else:
                vol_score = 50
        else:
            vol_score = 50

        # ======== 加权综合 ========
        composite = (
            ma_score * 0.30 +
            adx_score * 0.25 +
            channel_score * 0.25 +
            vol_score * 0.20
        )

        df.loc[df.index[idx], 'signal'] = round(max(0, min(100, composite)), 1)

    # 清理临时列
    df.drop(columns=['ma5', 'ma10', 'ma20', 'ma60', 'vol_ma10'], inplace=True)
    return df
