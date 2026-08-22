# AI 投研小组

基于 Hermes Agent 构建的结构化 AI 投研系统：**ERP 估值择时 + 红利配置 + ETF 技术风控 + 宏观逃顶**四层策略，配套数据管线与企微推送。

## 📂 仓库结构（按用途分类）

```
ai-investment-research/
├── strategies/                  ★ 策略库（按类型分类，核心）
│   ├── 01-ERP估值择时/           股债利差估值择时类
│   ├── 02-红利指数配置/          红利指数搭配类
│   ├── 03-ETF均线风控/          技术面趋势风控/同花顺公式
│   └── 04-宏观逃顶/             系统性风险闸门5
├── docs/                        系统性文档（主手册/数据规范/cron）
├── skills/                      投研角色技能（9角色）
├── scripts/                     回测与推送脚本
├── collectors/                  数据源采集器（P0官方优先）
├── config/ / db/ / validator/   数据管线配置/落库/校验
├── pipeline.py / erp_engine.py  数据管线主流程 + ERP 策略引擎
└── reports/                     历史盘中报告（归档）
```

## 🎯 四层策略架构

| 层 | 策略 | 关键规则 | 入口 |
|----|------|---------|------|
| **择时** | ERP 股债利差 | 沪深300盈利收益率 − 10Y国债，分档定投 | `strategies/01` |
| **配置** | 红利指数 | 512890底仓+510880进攻，5只档案 | `strategies/01`+`02` |
| **执行** | 均线风控 | 跌破5日线减/20日线清，同花顺公式 | `strategies/03` |
| **风控** | 宏观逃顶 | 萨姆规则/CapEx砍单/曲线去倒挂/巴菲特现金 | `strategies/04` |

## 🏦 当前持仓与标的

| 标的 | 角色 | 策略 |
|------|------|------|
| 560780 半导体设备ETF | 核心仓（A股半导体） | 均线趋势风控 |
| 513650 标普500ETF | 美股独立仓 | 择时/持底 |
| 000725 京东方A | 面板独立仓 | 均线纪律 |
| 场外基金(~5291) | 全球/科技 | 独立 |
| **红利配置（拟定）** | ERP红利底仓+进攻 | 512890+510880 |

> ⚠️ 已清仓：513310中韩半导体、589130科创芯片（README 不再列为持仓）。

## 📜 文档导航

| 文档 | 内容 |
|------|------|
| `strategies/01-ERP估值择时/510880-专属档位策略.md` | ★ 510880 进攻手定制版（重仓≥7%） |
| `strategies/01-ERP估值择时/512890-底仓定投策略.md` | 512890 红利低波底仓 |
| `strategies/01-ERP估值择时/红利ETF-适配档案.md` | 5只红利ETF ERP分档全景 |
| `strategies/03-ETF均线风控/同花顺买卖策略.md` | 可粘贴同花顺K线买卖公式 |
| `docs/AI投研小组-完整策略手册-v2.0.md` | 生产级主手册（1525行） |
| `docs/data-source-spec-v1.0.md` | 数据源规范（官方优先+Fail Closed） |
| `docs/cron-jobs.md` | 定时任务清单 |

## 🔧 快速使用

```bash
# ERP 当月决策（输出档位+买入金额）
~/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe \
  ~/ai-investment-research/scripts/erp_interval_dca_v2.py

# 510880 专属档位回测
~/AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe \
  ~/ai-investment-research/scripts/erp_510880_custom.py
```

## ⚠️ 免责声明
本系统仅作投研辅助与风险提示，不构成投资建议，所有交易动作由人工最终确认。