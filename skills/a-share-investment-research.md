---
name: a-share-investment-research
description: >
  A-share investment research using real financial data, supply chain bottleneck
  analysis (Serenity methodology), and QDII fund selection. Use when the user
  asks about A-share stocks, 半导体/科技 stock analysis, 真科技股 screening,
  supply chain analysis (产业链/供应链/卡点/瓶颈), QDII fund comparison,
  or any Chinese stock market research that needs real quarterly earnings data.
  Triggers: "A股分析", "真科技股", "产业链分析", "半导体基金", "QDII基金",
  "supply chain bottleneck", "which stocks have real orders".
---

# A-Share Investment Research Skill

Research workflow for Chinese A-share stocks using real financial data and
supply chain bottleneck analysis (Serenity-inspired methodology).

## Core Principles

1. ALWAYS use actual reported quarterly data, NEVER estimates or forecasts
2. User explicitly corrected: "我要看的是2026年真实数据" — always fetch latest
   actual disclosure from eastmoney API
3. Start from supply chain layers, rank scarce layers before ranking companies
4. Use Chinese language for all output unless user asks otherwise

## Step 1: Fetch Real Financial Data

Use eastmoney API to get actual quarterly earnings:

```
curl -s "https://datacenter-web.eastmoney.com/api/data/v1/get?sortColumns=UPDATE_DATE&sortTypes=-1&pageSize=4&pageNumber=1&reportName=RPT_LICO_FN_CPD&columns=ALL&filter=(SECURITY_CODE%3D%22{code}%22)"
```

Key fields:
- SECURITY_NAME_ABBR: stock name
- DATATYPE: report period (e.g., "2026年 一季报")
- QDATE: quarter identifier (e.g., "2026Q1")
- TOTAL_OPERATE_INCOME: revenue (divide by 1e8 for 亿元)
- PARENT_NETPROFIT: net profit (divide by 1e8 for 亿元)
- YSTZ: revenue YoY growth %
- SJLTZ: profit YoY growth %
- XSMLL: gross margin %
- WEIGHTAVG_ROE: ROE %

For stock price data (domestic only):
```
curl -s "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{code}&fields1=f1,f2,f3,f4,f5,f6,f7&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end={date}&lmt={days}"
```
- market: 1 for Shanghai (SH), 0 for Shenzhen (SZ)

## Step 2: Serenity Supply Chain Analysis Workflow

Follow this sequence for theme scans:

1. **Set scope**: Market (A-share/HK/US/global), theme, time window
2. **Translate to system change**: What physical/economic change drives demand?
3. **Map value chain**: downstream → integrators → modules → chips → equipment → materials → infrastructure
4. **Find scarce layers**: Low supplier count, long qualification, hard expansion, customer urgency signals
5. **Rank layers BEFORE companies**: Show the system logic before the ticker list
6. **Build company universe**: Aim for 20+ candidates, filter to top 3-7
7. **Gather evidence**: Prefer filings, announcements, earnings reports
8. **Rank by**: demand pressure, closeness to scarce layer, evidence quality, valuation gap

## Step 3: QDII Fund Analysis

For global exposure via QDII funds (Chinese funds investing overseas):

1. Get fund list from eastmoney ranking API:
```
curl -s "https://fund.eastmoney.com/data/rankhandler.aspx?op=ph&dt=kf&ft=qdii&rs=&gs=0&sc=6yzf&st=desc&sd={start_date}&ed={end_date}&qdii=&tabSubtype=,,,,,&pi=1&pn=100&dx=1&v=0.123" -H "Referer: https://fund.eastmoney.com/data/fundranking.html"
```

2. Get fund holdings from eastmoney:
```
curl -s "https://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10&year={year}&month={month}&rt=0.123" -H "Referer: https://fundf10.eastmoney.com/ccmx_{fund_code}.html"
```
Parse with regex: `r'<td[^>]*><a[^>]*>([^<]+)</a></td>.*?<td[^>]*>(\d+\.\d+)%</td>'`

3. Map holdings to supply chain layers, calculate exposure % per layer

## Output Format

Always use this structure for stock analysis:

```
======================================================================
  先排产业链层级，再排公司。
  优先级: [layer 1] > [layer 2] > [layer 3]
======================================================================

Tier 1: 产业链卡点 + 高增长
  [Stock] — [what it constrains]
    2026Q1: 营收X亿(+Y%)，净利润Z亿(+W%)，毛利率M%
    证据强度: 强/中/弱
    主要风险: ...

Tier 2: ...
======================================================================
```

## Network

Eastmoney API calls from the Hermes runtime require the local Clash Verge proxy. Always use `-x http://127.0.0.1:7890` with curl. Direct connections fail with exit code 49.

## Pitfalls

- **Proxy required**: All eastmoney curl calls must use `-x http://127.0.0.1:7890`
- Never present estimates as actual data — always verify report date
- Q1 reports typically available by late April, annual reports by late April
- Korean/Japanese stocks NOT available via eastmoney stock price API
- Fund holdings data may lag (check year/month params)
- Supply chain priority varies by user — ask or check memory for their specific chain

## Sector Analysis Context

- **Military stocks**: Q1 data is often weak due to seasonal delivery patterns (Q4 concentration). Always note this.
- **Growth vs value**: User specifically asks for "真科技股" — focus on revenue growth + margin stability + order backlog, not stories.
- **Light module stocks**: Often treated as cyclical, but AI demand may make them structural — flag this distinction.

## Step 4: Automated Semiconductor ETF Monitoring (Cron)

For recurring intraday monitoring of semiconductor ETFs, use the 9-node daily schedule with cron jobs pushing to WeCom (企业微信) group bot.

### Target ETFs
- 513310 (半导体设备ETF)
- 560780 (科创芯片ETF)
- 589130 (中韩半导体ETF)

### Data Sources
- **Korea real-time**: KIS Open API primary, pykrx backup (delayed)
- **A-share ETF intraday**: AkShare `fund_etf_spot_em` / `fund_etf_hist_min_em`
- **US semis**: yfinance / Alpha Vantage
- **DST handling**: Python `zoneinfo.ZoneInfo("America/New_York")` auto-detects EDT/EST

### Delivery
WeCom group bot webhook — POST markdown to `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={KEY}`.
Rate limit: 20 msg/min per bot, 2048 bytes per text message.

### Cron execution
Each node runs as a separate cron job with its own prompt. Deliver to the user's current chat (default) or WeCom webhook. The 21:10/22:10 DST switch is handled by the cron script, not manual config.
- **Position sizing**: reduce 589130→513310→560780; add 560780→513310→589130
- **No entry before 10:15** (filter 9:30-10:00 noise)
- **ETF trades prefer close** (avoid morning false breakouts)

## References

- `references/eastmoney-api.md` — Full API reference, stock codes, fund APIs
- `references/semiconductor-value-chain.md` — A-share semiconductor sector mapping and scarce layer analysis
- `references/qdii-fund-mapping.md` — Global QDII fund holdings mapped to supply chain layers
- `references/semiconductor-etf-monitoring.md` — Full 9-node intraday monitoring schedule with data sources, WeCom delivery, and DST handling
