# -*- coding: utf-8 -*-
"""
一次性拉取全部股票历史数据到本地，后续测试只读本地文件
主数据源：baostock（稳定免费）
"""

import baostock as bs
import pandas as pd
import os
import time

# ====================== 股票池（30只，覆盖各行业） ======================
STOCK_POOL = {
    # 消费
    "sh.600519": "贵州茅台", "sz.000858": "五粮液", "sz.000333": "美的集团",
    "sz.002594": "比亚迪",
    # 金融
    "sh.600036": "招商银行", "sh.601318": "中国平安", "sh.600030": "中信证券",
    "sh.601166": "兴业银行",
    # 新能源
    "sz.300750": "宁德时代", "sh.601012": "隆基绿能", "sz.300274": "阳光电源",
    # 医药
    "sh.600276": "恒瑞医药", "sz.300760": "迈瑞医疗", "sh.603259": "药明康德",
    # 科技
    "sh.688981": "中芯国际", "sz.002415": "海康威视", "sz.002475": "立讯精密",
    # 能源
    "sh.601088": "中国神华", "sh.600900": "长江电力", "sh.601225": "陕西煤业",
    # 化工
    "sh.600309": "万华化学", "sh.600426": "华鲁恒升", "sh.600160": "巨化股份",
    # 农业
    "sz.002714": "牧原股份", "sz.300498": "温氏股份", "sz.002311": "海大集团",
    # 交通
    "sh.601006": "大秦铁路", "sh.601872": "招商轮船", "sz.001965": "招商公路",
}

START_DATE = "2020-01-01"
END_DATE = "2026-07-08"
OUTPUT_DIR = "data/prices"


def fetch_one_stock(bs_code):
    """拉取单只股票全部历史数据"""
    rs = bs.query_history_k_data_plus(
        bs_code, "date,open,high,low,close,volume",
        start_date=START_DATE, end_date=END_DATE,
        frequency="d", adjustflag="2"  # 前复权
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
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 登录
    bs.login()
    print("baostock 登录成功\n")

    success = 0
    failed = []

    for bs_code, name in STOCK_POOL.items():
        code = bs_code.split('.')[1]  # sh.600519 → 600519
        output_path = f"{OUTPUT_DIR}/{code}.csv"

        print(f"[{code}] {name} ...", end=' ')

        try:
            df = fetch_one_stock(bs_code)
            if df is not None and len(df) > 200:
                df.to_csv(output_path, index=False)
                print(f"✅ {len(df)}条 ({df['date'].iloc[0].date()} → {df['date'].iloc[-1].date()})")
                success += 1
            else:
                print(f"❌ 数据不足({len(df) if df is not None else 0}条)")
                failed.append(f"{name}({code})")
        except Exception as e:
            print(f"❌ {str(e)[:40]}")
            failed.append(f"{name}({code})")

        time.sleep(0.5)  # 请求间隔

    bs.logout()

    # 保存股票池信息
    pool_df = pd.DataFrame([
        {'code': k.split('.')[1], 'bs_code': k, 'name': v, 'industry': ''}
        for k, v in STOCK_POOL.items()
    ])
    pool_df.to_csv("data/stock_list.csv", index=False)

    # 汇总
    print(f"\n{'='*50}")
    print(f"完成: {success}/{len(STOCK_POOL)} 只股票")
    if failed:
        print(f"失败: {', '.join(failed)}")
    print(f"数据目录: {OUTPUT_DIR}/")
    print(f"股票池: data/stock_list.csv")


if __name__ == "__main__":
    main()
