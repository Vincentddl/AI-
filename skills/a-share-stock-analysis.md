---
name: a-share-stock-analysis
description: "Analyze A-share (China) stocks using real financial data from Eastmoney API. Covers quarterly earnings, fund holdings, sector analysis, and supply-chain research. Use for requests like '分析A股', '半导体基金', '真科技股', '产业链分析', '财报数据', 'A-share analysis', 'sector screen', 'fund holdings lookup'."
version: 1.0.0
author: Hermes Agent
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [finance, stocks, a-share, china, semiconductor, analysis, eastmoney]
---

# A-Share Stock Analysis

Research and analyze Chinese A-share stocks using real financial data from Eastmoney (东方财富) APIs. No authentication required for most endpoints. Combine with the Serenity supply-chain methodology for deep sector analysis.

## When to Use

- User asks about A-share stocks, sectors, or industries
- User wants real financial data (quarterly earnings, revenue, profit)
- User wants fund holdings analysis (which fund holds which stocks)
- User wants supply-chain bottleneck analysis for Chinese tech sectors
- User asks about semiconductor, AI, robotics, defense, or new energy stocks

## Quick Start

1. Get quarterly earnings for specific stocks via Eastmoney API
2. Analyze revenue growth, profit growth, gross margin trends
3. Rank companies by certainty, technical barriers, and order strength
4. For fund analysis, look up holdings and calculate sector exposure

## Data Sources

All data comes from Eastmoney (东方财富) public APIs — no auth required.

- `references/eastmoney-api-patterns.md` — complete API endpoint reference

## Analysis Framework (Serenity Methodology)

For sector/theme analysis, follow this workflow:

1. **Translate theme into system change** — what technical/economic shift drives demand?
2. **Map the value chain** — downstream → system integrators → modules → chips → equipment → materials
3. **Find the scarce layer** — low supplier count, long qualification, hard expansion
4. **Build company universe** — aim for 20+ candidates before filtering to top 3-7
5. **Gather real evidence** — quarterly earnings, contract announcements, order backlog
6. **Rank by priority** — demand pressure, closeness to scarce layer, evidence quality
7. **Explain what could go wrong** — substitution, competition, demand weakness

## Key Pitfalls

### 1. Always filter by QDATE for latest data
The Eastmoney earnings API returns multiple quarters. Always filter for `QDATE == "2026Q1"` (or latest) when comparing companies. Sort by QDATE to see trends.

### 2. Revenue is in raw RMB, convert to 亿
Divide `TOTAL_OPERATE_INCOME` by 1e8 to get 亿 (100 million). Same for `PARENT_NETPROFIT`.

### 3. Fund holdings are from latest quarterly report
Fund holdings data is from the most recent quarterly disclosure (季报), not real-time. Holdings may have changed since the report date.

### 4. Field names in Eastmoney API
- `YSTZ` = 营收同比增长率 (revenue YoY growth %)
- `SJLTZ` = 净利润同比增长率 (profit YoY growth %)
- `XSMLL` = 销售毛利率 (gross margin %)
- `WEIGHTAVG_ROE` = 加权平均ROE
- `QDATE` = 报告期 (e.g. "2026Q1")
- `DATATYPE` = 报告期中文 (e.g. "2026年 一季报")

### 5. Fund ranking API returns JavaScript, not JSON
The fund ranking endpoint returns `var rankData = {datas:[...]}`. Parse by extracting the array between `datas:[` and `]`, then split by `","`.

### 6. A-share stock codes
- `6xxxxx` = Shanghai (prefix `1.` in secid: `1.688012`)
- `0xxxxx` / `3xxxxx` = Shenzhen (prefix `0.`: `0.002371`)

### 7. Network proxy required for eastmoney API
Eastmoney API calls from the Hermes runtime environment require the local Clash Verge proxy. Always use `-x http://127.0.0.1:7890` in curl commands. Direct connections return exit code 49 / empty output.

### 8. ETF price data uses kline API with secid
For A-share ETFs (513310, 560780, 589130, etc.), use the stock kline endpoint:
```
curl -s "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.513310&fields1=f1,f2,f3,f4,f5,f6,f7&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end=YYYYMMDD&lmt=5" -x http://127.0.0.1:7890
```
Kline format per line: date,open,close,high,low,volume,amount.

## Notification Delivery

WeCom (企业微信) group bot webhook is the primary notification channel. See `references/wecom-delivery.md` for format requirements and pitfalls.
