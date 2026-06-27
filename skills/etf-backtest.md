---
name: etf-backtest
description: >-
  ETF策略回测引擎 — 对513310/560780/589130的交易规则进行历史回测，
  验证胜率/盈亏比/最大回撤，输出闸门4判定(AI可读JSON)。
  Triggers: "回测", "验证策略", "闸门4", "历史回测", "策略有效吗",
  "这个规则能用吗", "backtest".
---

# ETF 策略回测引擎

## 调用方式

```python
import sys
sys.path.insert(0, r"C:\Users\Vincent Lu\AppData\Local\hermes\scripts")
from etf_backtest import run_backtest

result = run_backtest()  # 回测全部三只ETF
# 或单只: result = run_backtest(codes=["513310"])
```

返回 JSON 结构:
```json
{
  "run_at": "2026-06-28T...",
  "results": [
    {
      "code": "513310",
      "name": "中韩半导体",
      "best_strategy": "保守策略 (MA20)",
      "risk_assessment": {"level": "低/中/高", "reason": "..."},
      "strategies": [
        {"name": "保守策略", "trades": 6, "win_rate": 66.7,
         "profit_factor": 4.8, "total_return": 64.0,
         "max_drawdown": 9.8, "gate4": "passed/warning/blocked",
         "verdict": "有效/有瑕疵/无效"}
      ]
    }
  ],
  "overall_verdict": "✅全部通过 / ⚠️部分瑕疵 / 🔴被拦截",
  "action_items": ["具体建议"]
}
```

## 三种策略

| 策略 | 卖信号 | 买信号 | 特点 |
|------|--------|--------|------|
| 保守策略 (MA20) | 跌破MA20 或 暴跌放量(-5%+量比>2) | 站上MA10+MA10>MA20+放量 | 交易少、胜率高、回撤低 |
| 优化策略 (MA10) | 跌破MA10 或 放量长阴(-3%+量比>1.5) | 站上MA5+MA5>MA20+放量 | 平衡 |
| 基础策略 (MA5) | 跌破MA5/MA10 或 放量长阴 | 站上MA5+放量 | 交易频繁、噪音多 |

## AI 判定规则 (闸门4)

回测结果自动判定：
- **passed**: 胜率≥40% 且 回撤≤15% 且 连亏≤5 且 盈亏比≥1.5 → 闸门4放行
- **warning**: 仅1项不达标 → 放行但标注风险
- **blocked**: 2项及以上不达标 → 闸门4拦截，禁止实盘

## 使用频率

- **周频自动**: 周六 10:00 cron
- **手动触发**: 新规则上线前、策略调整后
- **AI 调用**: 任何需要验证交易规则有效性的场景

## 输出解读

- `risk_assessment.level = "低"` → 策略有效，可用
- `risk_assessment.level = "中"` → 可用但需关注 issues 字段
- `risk_assessment.level = "高"` → 不可用，必须修改策略
- `gate4 = "passed"` → 闸门4放行
- `gate4 = "blocked"` → 闸门4拦截
- `best_strategy` → 该ETF当前最优策略名称
