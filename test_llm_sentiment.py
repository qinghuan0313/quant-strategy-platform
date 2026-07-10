# -*- coding: utf-8 -*-
"""测试策略D的LLM真实情感分析"""
import sys; sys.path.insert(0, '.')
from strategies.strategy_d import call_llm_sentiment

with open('apikey.txt', 'r') as f:
    api_key = f.read().strip()

news_list = [
    ("贵州茅台出厂价上调20% 创近五年最大涨幅",
     "贵州茅台宣布自7月起将飞天茅台出厂价上调20%，这是五年来最大幅度提价。"),
    ("宁德时代三季度营收增速放缓至5%",
     "宁德时代发布三季报，营收同比增长5%，较上季度的15%增速明显放缓。"),
    ("招商银行公告召开年度股东大会",
     "招商银行发布公告，将于8月15日召开年度股东大会，审议利润分配方案等常规议案。"),
    ("牧原股份上半年预亏30亿 猪价持续低迷",
     "牧原股份发布业绩预告，预计上半年净亏损30-35亿元，主要受猪价持续低迷影响。"),
]

print("LLM新闻情感分析测试")
print("=" * 70)
for title, content in news_list:
    r = call_llm_sentiment(
        title, content,
        api_key=api_key,
        base_url='https://api.deepseek.com',
        model='deepseek-chat'
    )
    tag = r['sentiment']
    score = r['score']
    reason = r['reason']
    print(f"[{tag:>8}] 分数:{score:+4d}  理由:{reason}")
    print(f"         新闻:{title}")
    print()
