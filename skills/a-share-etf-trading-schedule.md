---
name: a-share-etf-trading-schedule
description: >-
  AI投研小组 — A股半导体ETF结构化分析系统。9角色 × 4风控闸门 × 9时间节点。
  覆盖513310/560780/589130/000725，外盘/韩国/美股联动，集合竞价/分时/尾盘决策。
  Triggers: "半导体ETF", "投研小组", "风控", "集合竞价", "尾盘调仓", "外盘扫描".
---

# AI投研小组：A股半导体ETF专用版

## 持仓

| Code | Name | Role | Strategy |
|------|------|------|----------|
| 513310 | 中韩半导体ETF | 外盘/韩国联动仓 | 受外盘影响最大，观察为主，不作为日内进攻主仓 |
| 560780 | 半导体设备ETF | 核心仓位，偏中线 | 最能扛波动，优先加仓对象，不因短期恐慌减仓 |
| 589130 | 科创芯片ETF | 弹性进攻仓 | 板块强时增强收益，板块弱时优先减仓 |
| 000725 | 京东方A | 面板独立仓 | 独立于半导体逻辑，不被半导体恐慌错杀 |

---

## 核心原则

1. **数据先行，观点后置** — 所有结论必须先引用行情、成交量、指数、外盘数据，禁止主观臆断。
2. **先证伪，再看多** — 每次加仓建议前必须先检查破位、放量下跌、高开低走、板块背离、外盘利空等风险。
3. **ETF ≠ 个股** — 分析重点是成分/板块景气度/成交量/溢价折价/资金流/均线/外盘传导，不是单公司财报。
4. **日内 vs 中线分开** — 盘中任务只输出短线动作；周度/月度才讨论中线配置。
5. **回测优先于主观** — 新增交易规则必须先回测验证。

---

## 四道风控闸门 ⛔

分析时必须逐道检查，任何一道未通过则降级处理。

### 闸门1：数据闸门
**触发条件**: 行情数据缺失 / 延迟严重 / 接口异常
**结果**: 禁止输出加仓建议，只能输出「观察」。标注数据可信度等级。

### 闸门2：趋势闸门
**触发条件**: ETF 跌破 10 日线 且 半导体板块同步走弱
**结果**: 禁止加仓。只允许「持有」或「减仓」。

### 闸门3：风险官闸门
**触发条件**: 风险官给出「高风险」评级
**结果**: 所有看多建议降级处理（加仓→观察，观察→减仓）。

### 闸门4：回测闸门
**触发条件**: 新规则未经历史回测验证
**结果**: 不允许用于仓位调整，只能进入观察名单。

---

## 风险官规则：10条减仓触发条件

出现以下**任意一条**，风险官标记对应等级：

| # | 条件 | 等级 |
|---|------|------|
| 1 | 跌破5日线后30分钟内不能收回 | ⚠️ 中 |
| 2 | 跌破10日线且半导体板块同步走弱 | 🔴 高 |
| 3 | 跌破20日线 | 🔴 高 |
| 4 | 高开低走（开盘+2%以上→收盘翻绿） | ⚠️ 中 |
| 5 | 放量长阴（跌幅>3%且量比>1.5） | 🔴 高 |
| 6 | 外盘半导体大跌（SOX单日<-3% 或 NVDA<-5%） | ⚠️ 中 |
| 7 | 韩国半导体走弱（SK海力士/三星<-3%） | ⚠️ 中 |
| 8 | A股半导体板块弱于大盘（板块涨幅<大盘涨幅-1%） | 🟡 低 |
| 9 | 成交量异常萎缩（量比<0.5） | 🟡 低 |
| 10 | 513310出现明显溢价或折价异常（偏离净值>2%） | ⚠️ 中 |

**风险官输出格式**: `风险等级: 低/中/高 | 允许加仓: 是/否 | 必须减仓: 是/否 | 只允许观察: 是/否`

---

## 加仓与减仓条件

### 加仓条件（5条全部满足才允许）

1. 半导体板块强于大盘（板块涨幅 ≥ 大盘涨幅）
2. 目标 ETF 站上 5 日线
3. 成交量不明显萎缩（量比 ≥ 0.7）
4. 风险官未给出「中」或「高」风险
5. 没有高开低走迹象

**加仓幅度**: 每次最多 10%，不允许一次性满仓。

### 减仓条件（满足任意1条即考虑）

1. 跌破5日线后无法收回
2. 跌破10日线且板块走弱
3. 跌破20日线
4. 放量长阴
5. 美股半导体和韩国半导体同步走弱
6. 589130明显弱于560780和513310

**减仓优先级**: 589130 → 513310 → 560780
**加仓优先级**: 560780 → 513310 → 589130
**京东方A**: 独立判断，不列入半导体风控序列

---

## 决策秘书：标准输出格式

所有时间节点分析必须按此格式输出：

```
市场状态: 强 / 中性 / 弱
外盘影响: 利好 / 中性 / 利空
韩国半导体: 走强 / 震荡 / 走弱
板块vs大盘: 强于 / 同步 / 弱于
────────────────
最强ETF: {code}  {理由}
最弱ETF: {code}  {理由}
────────────────
风控闸门: ①数据✅/❌ ②趋势✅/❌ ③风险官✅/❌ ④回测✅/❌
风险等级: 低 / 中 / 高
────────────────
今日动作: 持有 / 观察 / 加仓10% / 减仓10%-20% / 降到观察仓
理由: {数据支撑的具体原因}
风险提示: {最大风险点}
下一次检查时间: {下一个节点}
是否需要人工确认: 是 / 否
```

---

## 数据源

### 总览

```
A股 ETF ──→ Eastmoney (直连) ⭐
美股个股 ──→ Yahoo API (代理) → Tencent (直连备胎)
SOX 指数 ──→ Yahoo API (代理)
韩国市场 ──→ Yahoo API (代理) → Tencent (直连备胎)
汇率    ──→ fawazahmed0 CDN (代理) → Sina (直连备胎)
```

### A-share ETF — Eastmoney (直连)

```bash
# 实时行情
curl -s "https://push2.eastmoney.com/api/qt/stock/get?secid=1.{code}&fields=f43,f44,f45,f46,f47,f48,f50,f170,f171"

# 日K线 (最新20根) — MA5/MA10/MA20/布林带计算
curl -s "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.{code}&fields1=f1,f2,f3,f4,f5,f6,f7&fields2=f51,f52,f53,f54,f55,f56,f57&klt=101&fqt=1&end={yyyymmdd}&lmt=20"

# 1分钟K线 (分时, 240根=1天)
curl -s "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=1.{code}&fields1=f1,f2,f3,f4,f5,f6,f7&fields2=f51,f52,f53,f54,f55,f56,f57&klt=1&fqt=1&end={yyyymmdd}&lmt=240"
```

K-line: `date,open,close,high,low,volume,amount`
Spot: f43=最新价, f170=涨跌幅%, f46=开盘, f47=成交量, f50=量比

### US Stocks — Yahoo API (代理) → Tencent (直连)

```bash
# Primary: Yahoo Finance
curl -s --max-time 10 "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d" \
  -x http://127.0.0.1:7890 -H "User-Agent: Mozilla/5.0"
# JSON: chart.result[0].meta.regularMarketPrice / chartPreviousClose
#       chart.result[0].indicators.quote[0].close[] = K线

# Fallback: Tencent (直连)
curl -s --max-time 5 "https://qt.gtimg.cn/q=us{ticker}"
# 按~分割: [3]=最新价, [4]=昨收, [32]=涨跌幅%, [33]=最高, [34]=最低
```

Tickers: NVDA, AMD, ASML, AMAT, KLAC, TSM

### SOX — Yahoo only

```bash
curl -s --max-time 10 "https://query1.finance.yahoo.com/v8/finance/chart/^SOX?interval=1d&range=5d" \
  -x http://127.0.0.1:7890 -H "User-Agent: Mozilla/5.0"
```

### Korea — Yahoo (代理) → Tencent (直连)

```bash
# Primary: Yahoo
# Symbols: 005930.KS=三星, 000660.KS=SK海力士, ^KS11=KOSPI, ^KQ11=KOSDAQ
curl -s --max-time 10 "https://query1.finance.yahoo.com/v8/finance/chart/005930.KS?interval=1d&range=5d" \
  -x http://127.0.0.1:7890 -H "User-Agent: Mozilla/5.0"

# Fallback: Tencent
curl -s --max-time 5 "https://qt.gtimg.cn/q=kr005930"   # 三星
curl -s --max-time 5 "https://qt.gtimg.cn/q=kr000660"   # SK海力士
```

### Exchange Rates — fawazahmed0 CDN (代理) → Sina (直连)

```bash
# Primary: fawazahmed0 (开源免费)
curl -s --max-time 8 "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json" \
  -x http://127.0.0.1:7890
# JSON: usd.cny, usd.krw

# Fallback: Sina
curl -s "https://hq.sinajs.cn/list=fx_susdcny" -H "Referer: https://finance.sina.com.cn"
```

---

## 每日运行流程 (9节点)

### 08:50 外盘+韩国早盘预判
- 拉取美股半导体隔夜收盘 + 韩国开盘50分钟 + 汇率
- 判断今日A股半导体偏强/中性/偏弱
- **不给买卖指令**

### 09:26 集合竞价确认
- 四只持仓（含000725京东方A）开盘价/竞价量/距均线
- 高开低走风险 / 低开修复机会 / 放量突破可能 / 不适合交易
- 京东方A独立标注（不套用半导体风控）
- **禁止追买**

### 10:15 第一决策点
- 四只持仓开盘45分钟分时，过滤9:30-10:00情绪
- 站上分时均线？放量？板块vs大盘？科创共振？
- **当信号矛盾时**（如价涨量缩、或ETF之间方向不一致），启动多空辩论：
  ```python
  delegate_task(
    tasks=[
      {"goal": "多头视角分析{ETF}，给出加仓理由和证据", "context": "当前数据: ..."},
      {"goal": "空头视角分析{ETF}，给出减仓/观望理由和证据", "context": "当前数据: ..."},
      {"goal": "风控视角检查{ETF}，按10条风险官规则逐条判断", "context": "当前数据: ..."},
    ],
    toolsets=["terminal", "file"]
  )
  ```
  汇总三方观点后输出: 持有 / 加仓10% / 减仓10-20% / 观望
- **必须检查四道风控闸门**
- 京东方A独立标注

### 14:40 尾盘调仓决策
- 四只持仓全天+韩国收盘+均线
- **当ETF之间强弱方向不一致时，启动多空辩论**（同上10:15模式）
- 减仓: 589130→513310→560780（京东方独立）
- 加仓: 560780→513310→589130
- **必须通过四道风控闸门**

### 16:10 收盘归档
- 四只持仓收盘价/涨跌幅/成交量/均线状态
- 明日三预案: 高开/平开/低开
- 京东方A独立预案
- 支撑位/压力位/止损条件分时均线？放量？板块vs大盘？科创共振？
- **当信号矛盾时**（如价涨量缩、或ETF之间方向不一致），启动多空辩论：
  ```python
  delegate_task(
    tasks=[
      {"goal": "多头视角分析{ETF}，给出加仓理由和证据", "context": "当前数据: ..."},
      {"goal": "空头视角分析{ETF}，给出减仓/观望理由和证据", "context": "当前数据: ..."},
      {"goal": "风控视角检查{ETF}，按10条风险官规则逐条判断", "context": "当前数据: ..."},
    ],
    toolsets=["terminal", "file"]
  )
  ```
  汇总三方观点后输出: 持有 / 加仓10% / 减仓10-20% / 观望
- **必须检查四道风控闸门**
- 京东方A独立标注

### 14:40 尾盘调仓决策
- 四只持仓全天+韩国收盘+均线
- **当ETF之间强弱方向不一致时，启动多空辩论**（同上10:15模式）
- 减仓: 589130→513310→560780（京东方独立）
- 加仓: 560780→513310→589130
- **必须通过四道风控闸门**

### 16:10 收盘归档
- 四只持仓收盘价/涨跌幅/成交量/均线状态
- 明日三预案: 高开/平开/低开
- 京东方A独立预案
- 支撑位/压力位/止损条件

### 21:10/22:10 美股夜间预警
- zoneinfo自动判断EDT/EST
- SOX/NVDA/AMD/ASML...开盘方向
- 仅T+1预警，不涉当日A股

### 00:30 美股异动监控
- 无异动→「无新增风险」；有异动→记录为次日08:50输入

---

## WeCom 推送

```python
import sys
sys.path.insert(0, r"C:\Users\Vincent Lu\AppData\Local\hermes\scripts")
from wecom_send import send_markdown
send_markdown(report)
```

---

## AI投研小组：关联 Skill

| 角色 | Skill | 频率 |
|------|-------|------|
| ② 产业链分析师 | `serenity-supply-chain` | 日频早盘+周频深度 |
| ④ 成分股分析师 | `stock-deep-analysis` | 周频/事件驱动 |
| ⑤ 价值审查员 | `value-investing-check` | 月频/大幅加仓前 |
| ⑥ 多Agent投委会 | `delegate_task` 并行 | 重大决策节点 |
| ⑦ 风险官 | 本 skill 内置(10条规则) | 每个决策点 |
| ⑧ 回测验证员 | `etf_backtest.py` (本地脚本) | 周频/新规则上线前 |
| ⑥ 多Agent投委会 | `delegate_task` 并行 | 10:15/14:40信号矛盾时触发 |

> ②④⑤⑥⑧ 在对应频率或触发条件满足时，加载对应 skill 运行。
> ⑧ `etf-backtest` 直接调用 `run_backtest()` 函数，输出 JSON + AI 判定 + 闸门4状态。
> 三种策略对比（基础MA5/优化MA10/保守MA20），保守策略(MA20)表现最优。
> QuantDinger 因需 Docker+虚拟化，当前不可用；`etf_backtest.py` 为直接替代。

## 参考文件

- `references/data-source-test-results.md` — 全市场数据源对比测试结果（2026-06-28）
- `references/quantdinger-deployment.md` — QuantDinger 部署前置条件与绕过方案
- `references/weekend-analysis-template.md` — 周末持仓分析模板

## Pitfalls

1. 周末/节假日无A股交易，检查 `datetime.date.today().weekday()`。
2. 数据源失败不报错——标记「数据闸门❌」并降级为观察。
3. 集合竞价数据只在 09:25 后有效。
4. WeCom markdown_v2 上限 ~4096 字符，精简输出。
5. 用 `zoneinfo.ZoneInfo` 判断 EDT/EST，不硬编码美股开盘时间。
6. 代理 `http://127.0.0.1:7890` 已验证通。Yahoo 超时改 10 秒重试。
7. **先跑风控闸门，再出结论**——不要先有结论再补风控。
8. 持仓四只: 513310/560780/589130/000725。京东方独立判断。
9. 禁止使用「看情况」「可能」「大概率」等模糊表述。
11. **Cron 必须 `approvals.mode: smart`** — 默认 `manual` 模式会让每个 shell 命令弹 "Run" 按钮，cron 在后台无人点击会卡死。已设为 smart (低风险自动放行)。
12. **回测已验证: 保守策略(MA20)优于频繁交易** — 详见 `references/backtest-findings.md`。
