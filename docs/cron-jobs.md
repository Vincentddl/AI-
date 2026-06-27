# Cron 任务配置

以下为 Hermes Agent 中的 12 个 cron 任务定义。可通过 `cronjob` 工具或 `hermes cron` CLI 创建。

## 日内监控 (9个)

### ① 08:50 外盘+韩国早盘预判
```
schedule: 50 8 * * 1-5
skill: a-share-etf-trading-schedule
toolsets: terminal, file
```

### ② 09:26 A股集合竞价确认
```
schedule: 26 9 * * 1-5
skill: a-share-etf-trading-schedule
toolsets: terminal, file
```

### ③ 10:15 第一交易决策点
```
schedule: 15 10 * * 1-5
skill: a-share-etf-trading-schedule
toolsets: terminal, file
```
信号矛盾时自动触发多空辩论（delegate_task 并行3子agent）

### ④ 11:35 上午收盘复盘
```
schedule: 35 11 * * 1-5
skill: a-share-etf-trading-schedule
toolsets: terminal, file
```

### ⑤ 13:20 午后趋势确认
```
schedule: 20 13 * * 1-5
skill: a-share-etf-trading-schedule
toolsets: terminal, file
```

### ⑥ 14:40 尾盘调仓决策
```
schedule: 40 14 * * 1-5
skill: a-share-etf-trading-schedule
toolsets: terminal, file
```
信号矛盾时自动触发多空辩论

### ⑦ 16:10 A股收盘归档
```
schedule: 10 16 * * 1-5
skill: a-share-etf-trading-schedule
toolsets: terminal, file
```

### ⑧ 21:10 美股半导体夜间预警
```
schedule: 10 21 * * 1-5
skill: a-share-etf-trading-schedule
toolsets: terminal, file
```
夏令时自动判断（zoneinfo），冬令时需调整为22:10

### ⑨ 00:30 美股盘中异动监控
```
schedule: 30 0 * * 2-6
skill: a-share-etf-trading-schedule
toolsets: terminal, file
```
周二~周六运行（对应美股周一~周五盘中）

## 周度任务 (3个)

### ⑩ 周六 10:00 策略回测（闸门4）
```
schedule: 0 10 * * 6
skill: a-share-etf-trading-schedule
script: etf_backtest.py
```
脚本先跑回测输出JSON → AI解读 → 判定闸门4 → 推企微

### ⑪ 周六 16:30 周末持仓周报
```
schedule: 30 16 * * 6
skill: a-share-etf-trading-schedule
```
四只持仓全周总结 + 下周预案 + 京东方独立判断

## 部署方式

在 Hermes Agent 中通过 `cronjob` 工具或 CLI 逐条创建。所有任务使用:
- model: deepseek-v4-pro (可通过 hermes model 切换)
- deliver: local (结果推企微通过 wecom_send.py 实现)
- 审批模式: smart (hermes config set approvals.mode smart)
