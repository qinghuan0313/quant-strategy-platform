# -*- coding: utf-8 -*-
"""拉取40只股票池全部数据到本地"""

import baostock as bs
import pandas as pd
import os
import time

STOCKS = {
    # 原有20只
    "sh.601088": "中国神华", "sh.600900": "长江电力", "sz.002714": "牧原股份",
    "sh.601225": "陕西煤业", "sh.600188": "兖矿能源", "sh.600036": "招商银行",
    "sh.600309": "万华化学", "sh.601006": "大秦铁路", "sh.600011": "华能国际",
    "sh.600795": "国电电力", "sz.000876": "新希望", "sh.601872": "招商轮船",
    "sh.600426": "华鲁恒升", "sz.002064": "华峰化学", "sh.600160": "巨化股份",
    "sh.601898": "中煤能源", "sh.601985": "中国核电", "sz.300498": "温氏股份",
    "sz.002311": "海大集团", "sz.001965": "招商公路",
    # 新增20只
    "sh.600519": "贵州茅台", "sz.000858": "五粮液", "sz.000333": "美的集团",
    "sz.002594": "比亚迪", "sh.600887": "伊利股份", "sh.601318": "中国平安",
    "sh.600030": "中信证券", "sh.601166": "兴业银行", "sh.600276": "恒瑞医药",
    "sz.300760": "迈瑞医疗", "sh.603259": "药明康德", "sz.300750": "宁德时代",
    "sz.002415": "海康威视", "sz.002475": "立讯精密", "sz.300274": "阳光电源",
    "sh.688981": "中芯国际", "sz.000651": "格力电器", "sh.600585": "海螺水泥",
    "sh.601857": "中国石油", "sh.688111": "金山办公",
}

START_DATE = "2020-01-01"
END_DATE = "2026-07-13"
OUTPUT_DIR = "data/prices"
os.makedirs(OUTPUT_DIR, exist_ok=True)

bs.login()
print("baostock login success\n")

ok, fail = 0, []
for bs_code, name in STOCKS.items():
    code = bs_code.split(".")[1]
    try:
        rs = bs.query_history_k_data_plus(
            bs_code, "date,open,high,low,close,volume",
            start_date=START_DATE, end_date=END_DATE,
            frequency="d", adjustflag="2"
        )
        data = []
        while (rs.error_code == '0') & rs.next():
            data.append(rs.get_row_data())
        if data:
            df = pd.DataFrame(data, columns=rs.fields)
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            df.to_csv(f"{OUTPUT_DIR}/{code}.csv", index=False)
            print(f"OK {code} {name}  {len(df)}条")
            ok += 1
        else:
            print(f"X  {code} {name}  无数据")
            fail.append(f"{name}({code})")
    except Exception as e:
        print(f"X  {code} {name}  {str(e)[:40]}")
        fail.append(f"{name}({code})")
    time.sleep(0.3)

bs.logout()

# 保存股票池
pool = [{"code": k.split('.')[1], "name": v} for k, v in STOCKS.items()]
pd.DataFrame(pool).to_csv("data/stock_list.csv", index=False)
print(f"\nDone: {ok}/{len(STOCKS)} OK")
if fail:
    print(f"Failed: {', '.join(fail)}")
