# 跨市场投资 Agent 数据来源与故障切换规范 v1.0

> 状态：已采纳，作为系统唯一数据源白名单
> 核心原则：官方优先、可执行备用、关键指标失败则熔断（Fail Closed）
> 最高准则：**NO DATA > WRONG DATA**（宁可无结论，不拼数字）

---

## 1. 覆盖范围

系统只维护以下市场：

### 中国（完整维护）
- 沪市全部 A 股
- 深市全部 A 股
- 北交所全部股票
- 沪深全部 ETF
- 沪深300
- 中证红利等策略需要的中证指数
- 中国国债收益率

### 美国（只维护）
- S&P 500
- Nasdaq Composite
- Nasdaq-100
- 美国国债收益率

### 日本（只维护）
- TOPIX
- Nikkei 225

### 韩国（只维护）
- KOSPI
- KOSDAQ

不建立美日韩完整股票数据库。

---

## 2. 数据源等级

| 等级 | 定义 | 是否允许直接产生交易信号 |
| -- | ----------------------------- | --------------- |
| P0 | 交易所、指数公司、央行、财政部等官方源 | ✅ |
| P1 | 官方 API 的可靠封装或官方数据转发 | ✅，必须保留来源信息 |
| P2 | Tushare、Alpha Vantage 等规范聚合服务 | ✅，需经过 Validator |
| P3 | 东方财富、腾讯、Yahoo、Stooq 等网页/聚合源 | ⚠️ 只能备用 |

原则：**P0 > P1 > P2 > P3**。LLM 不允许自行改变优先级。

---

## 3. 同源备用 ≠ 独立验证

```text
ChinaBond 官方接口 → AKShare bond_china_yield
```

AKShare 底层仍来自 ChinaBond，只能算**同源备用通道（transport backup）**，不能独立验证 ChinaBond 数据。

系统必须记录 `upstream_source`：
```text
provider = AKSHARE
upstream_source = CHINABOND
```

---

## 4-20. 各市场数据源明细（见附录总表）

---

## 21. sources.yaml 配置

```yaml
version: "1.0"

cn:
  stock_master:
    primary: SSE_SZSE_BSE
    fallback_1: TUSHARE_STOCK_BASIC
    fallback_2: AKSHARE

  stock_daily:
    primary: TUSHARE_DAILY
    fallback_1: AKSHARE_EASTMONEY
    fallback_2: AKSHARE_TENCENT

  etf_master:
    primary: SSE_SZSE
    fallback_1: TUSHARE_ETF_BASIC
    fallback_2: AKSHARE

  etf_daily:
    primary: TUSHARE_FUND_DAILY
    fallback_1: AKSHARE_ETF_EASTMONEY
    fallback_2: AKSHARE_ETF_SINA

  csindex_valuation:
    primary: CSINDEX_OFFICIAL
    fallback_1: AKSHARE_CSINDEX
    fail_policy: HARD_STOP

  gov_10y:
    primary: CHINABOND_OFFICIAL
    fallback_transport: AKSHARE_CHINABOND
    fallback_independent: TUSHARE_YC_CB
    fail_policy: HARD_STOP

us:
  sp500:
    primary: FRED_SP500
    fallback_1: SPDJI_OFFICIAL
    fallback_2: PUBLIC_MARKET_PROVIDER

  nasdaq_composite:
    primary: FRED_NASDAQCOM
    fallback_1: NASDAQ_OFFICIAL
    fallback_2: PUBLIC_MARKET_PROVIDER

  nasdaq100:
    primary: FRED_NASDAQ100
    fallback_1: NASDAQ_OFFICIAL
    fallback_2: PUBLIC_MARKET_PROVIDER

  gov_10y:
    primary: US_TREASURY
    fallback_1: FRED_DGS10
    fail_policy: HARD_STOP

jp:
  nikkei225:
    primary: NIKKEI_OFFICIAL_CSV
    fallback_1: NIKKEI_OFFICIAL_WEB
    fallback_2: PUBLIC_MARKET_PROVIDER

  topix:
    primary: JQUANTS_LIGHT
    fallback_1: JPX_OFFICIAL_WEB
    fallback_2: PUBLIC_MARKET_PROVIDER

kr:
  kospi:
    primary: KRX_OPEN_API
    fallback_transport: KRX_WEB
    fallback_2: PUBLIC_MARKET_PROVIDER

  kosdaq:
    primary: KRX_OPEN_API
    fallback_transport: KRX_WEB
    fallback_2: PUBLIC_MARKET_PROVIDER
```

---

## 22. 故障切换算法

每个指标严格执行：

```
① 请求 Primary → ② Schema验证 → ③ 单位验证 → ④ 日期验证 → ⑤ 数值异常检测
→ PASS? → YES=VALIDATED / NO=FALLBACK
```

Primary 失败 + Fallback 通过 → `quality = DEGRADED`
关键指标只有 P3 数据 → `quality = UNTRUSTED`, `decision = NO_SIGNAL`

---

## 23. 关键指标必须 Fail Closed

以下指标失败时**不得凑数据**：
- 沪深300 PE
- 中证红利 PE
- 中证红利股息率
- CN10Y
- US10Y（如果策略使用）

失败时 Agent 只能说："本期估值数据不可验证，暂停生成新的 ERP 交易信号。"
**禁止**从新闻/博客临时抓一个 PE 继续计算。

---

## 24. 数据日期规则

每条数据保存：`as_of_date` / `published_at` / `fetched_at` / `market_timezone`

组合指标取 `latest common date`，不混用不同日期的源。

---

## 25. 数据差异阈值

| 指标 | Warning | Hard Stop |
| ------------- | -------: | -----------: |
| 指数收盘价 | 0.05% | **0.15%** |
| 股票/ETF原始收盘 | 0.1% | **0.5%** |
| PE | 1% | **2%** |
| 股息率 | 0.05 pct | **0.10 pct** |
| CN10Y / US10Y | 3 bp | **5 bp** |
| 证券代码/名称 | — | **任何不一致** |

---

## 26. 单位规范

利率 = percentage points（百分点），内部统一存 `1.69` 表示 1.69%，不存 `0.0169`。

```python
erp = 100.0 / pe - yield_10y
```

---

## 27. 数据血缘（必存字段）

```text
metric / symbol / as_of_date / value / unit
provider / upstream_source / source_priority
raw_payload_hash / fetched_at
validation_status / validator_version
```

---

## 28. 采集频率

- A股：股票日线/ETF日线/指数估值每日盘后，CN10Y 每日，证券主数据每周
- 美国：指数每日收盘后，US10Y 每日
- 日本/韩国：每日当地收盘后

**日频采集，月频使用**。

---

## 30. Agent 约束（最高）

Agent **不得**：
- 自己寻找新数据源
- 自己猜 Ticker / API 字段
- 自己改变数据单位
- 用新闻里的估值替代数据库
- 自己修改 BUY/WAIT

Agent **唯一允许**：
- 调用 Collector → 查看 Validator → 调用 Strategy Engine → 解释结构化结果

**NO DATA > WRONG DATA**

---

## 附录：数据源总表（白名单）

| 数据 | Primary | Backup 1 | Backup 2 |
| ---------------- | ------------------ | ----------------- | --------------- |
| A股证券身份 | SSE/SZSE/BSE | Tushare | AKShare |
| A股日线 | Tushare | AKShare-EastMoney | AKShare-Tencent |
| ETF身份 | SSE/SZSE | Tushare | AKShare |
| ETF日线 | Tushare | EastMoney | Sina |
| 沪深300 PE | **CSIndex** | AKShare-CSIndex | **失败则停** |
| 中证红利 PE/DY | **CSIndex** | AKShare-CSIndex | **失败则停** |
| 中国10Y | **ChinaBond** | AKShare-ChinaBond | Tushare yc_cb |
| S&P500 | **FRED SP500** | S&P官方 | 公共行情源 |
| Nasdaq Composite | **FRED NASDAQCOM** | Nasdaq官方 | 公共行情源 |
| Nasdaq-100 | **FRED NASDAQ100** | Nasdaq官方 | 公共行情源 |
| 美国10Y | **US Treasury** | **FRED DGS10** | 失败则停 |
| Nikkei225 | **Nikkei官方CSV** | Nikkei网页 | 公共行情源 |
| TOPIX | **J-Quants Light** | JPX官方 | 公共行情源 |
| KOSPI | **KRX Open API** | KRX网页 | 公共行情源 |
| KOSDAQ | **KRX Open API** | KRX网页 | 公共行情源 |

任何未列入表的来源默认 `NOT_APPROVED`，不得参与正式交易信号计算。

---

## 参考链接

[1] AKShare 债券数据 https://akshare.akfamily.xyz/data/bond/bond.html
[2] 北京证券交易所股票列表 https://www.bse.cn/nq/listedcompany.html
[3] Tushare daily https://tushare.pro/document/1?doc_id=27
[4] AKShare 股票数据 https://akshare.akfamily.xyz/data/stock/stock.html
[5] 上交所 ETF 列表 https://www.sse.com.cn/assortment/fund/etf/list/
[6] Tushare etf_basic https://tushare.pro/document/2?doc_id=385
[7] Tushare fund_daily https://tushare.pro/document/1?doc_id=108
[8] AKShare 公募基金 https://akshare.akfamily.xyz/data/fund/fund_public.html
[9] AKShare 指数数据 https://akshare.akfamily.xyz/data/index/index.html
[10] FRED series/observations https://fred.stlouisfed.org/docs/api/fred/series_observations.html
[11] FRED SP500 https://fred.stlouisfed.org/series/sp500
[12] FRED NASDAQCOM https://fred.stlouisfed.org/series/NASDAQCOM
[13] FRED NASDAQ100 https://fred.stlouisfed.org/series/NASDAQ100/
[14] S&P Global 数据能力 https://www.spglobal.com/spdji/
[15] U.S. Treasury 每日收益率 https://home.treasury.gov/resource-center/data-chart-center/interest-rates/
[16] Nikkei 指数信息 https://indexes.nikkei.co.jp/en/nkave/index/profile
[17] JPX TOPIX https://www.jpx.co.jp/english/markets/indices/topix/index.html
[18] J-Quants API 计划 https://www.jpx.co.jp/english/corporate/news/news-releases/6020/20250822-01.html
[19] KRX Open API 服务列表 https://openapi.krx.co.kr/
[20] KRX Open API 使用方法 https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO003.jsp
