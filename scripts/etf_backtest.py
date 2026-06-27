#!/usr/bin/env python3
"""
A-share ETF 回测引擎 — AI Agent 原生支持
===========================================
输出: JSON (给 AI 读) 或 文本 (给人读)
用法:
  python3 etf_backtest.py                    # 文本输出，回测全部
  python3 etf_backtest.py --json             # JSON 输出，AI 可解析
  python3 etf_backtest.py --json --code 513310  # 单只 JSON

JSON 输出结构:
{
  "run_at": "2026-06-28T12:00:00",
  "data_range": {"from": "2025-06-17", "to": "2026-06-26", "bars": 250},
  "results": [
    {
      "code": "513310", "name": "中韩半导体",
      "strategies": [
        {"name": "保守策略", "trades": 6, "win_rate": 66.7, "profit_factor": 4.8,
         "total_return": 64.0, "max_drawdown": 9.8, "verdict": "有效", "recommendation": "..."}
      ],
      "best_strategy": "保守策略",
      "risk_assessment": {"level": "低", "reason": "..."}
    }
  ],
  "overall_verdict": "所有策略在回测期内有效",
  "action_items": ["闸门4: 保守策略回测通过", "560780 胜率67%符合核心仓定位"]
}
"""

import json, urllib.request, sys, math
from datetime import datetime, date, timedelta

PROXY = "http://127.0.0.1:7890"
ETF_CODES = {"513310": "中韩半导体", "560780": "半导体设备", "589130": "科创芯片"}

# ============================================================
# 数据
# ============================================================

def fetch_kline(code, days=250):
    secid = f"1.{code}" if code.startswith("5") else f"0.{code}"
    today = date.today().strftime("%Y%m%d")
    url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get?"
           f"secid={secid}&fields1=f1,f2,f3,f4,f5,f6,f7"
           f"&fields2=f51,f52,f53,f54,f55,f56,f57"
           f"&klt=101&fqt=1&end={today}&lmt={days}")
    ph = urllib.request.ProxyHandler({"https": PROXY, "http": PROXY})
    resp = urllib.request.build_opener(ph).open(
        urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=10)
    data = json.loads(resp.read().decode())["data"]["klines"]
    return [{"date": k.split(",")[0], "open": float(k.split(",")[1]),
             "close": float(k.split(",")[2]), "high": float(k.split(",")[3]),
             "low": float(k.split(",")[4]), "volume": int(k.split(",")[5])}
            for k in data]

# ============================================================
# 回测核心
# ============================================================

def backtest(data, rules, warmup=30):
    n = len(data)
    closes = [d["close"] for d in data]
    volumes = [d["volume"] for d in data]
    position = 0; entry_price = 0; trades = []

    for i in range(warmup, n - 1):
        today = data[i]; yesterday = data[i - 1]
        ma5 = sum(closes[i-5:i]) / 5
        ma10 = sum(closes[i-10:i]) / 10
        ma20 = sum(closes[i-20:i]) / 20
        avg_vol20 = sum(volumes[max(0,i-20):i]) / min(20, i)
        chg = (today["close"] - yesterday["close"]) / yesterday["close"] * 100
        vol_ratio = today["volume"] / avg_vol20 if avg_vol20 > 0 else 1

        ctx = {"close": today["close"], "ma5": ma5, "ma10": ma10, "ma20": ma20,
               "chg": chg, "vol_ratio": vol_ratio}

        signal = "hold"
        for rule in rules.get("sell", []):
            if rule["condition"](ctx): signal = "sell"; break
        if position == 0:
            for rule in rules.get("buy", []):
                if rule["condition"](ctx): signal = "buy"; break

        next_day = data[i + 1]
        if signal == "buy" and position == 0:
            position = 1; entry_price = next_day["open"]
            trades.append({"type": "buy", "date": next_day["date"], "price": entry_price})
        elif signal == "sell" and position == 1:
            position = 0; exit_price = next_day["open"]
            pnl = (exit_price - entry_price) / entry_price * 100
            trades.append({"type": "sell", "date": next_day["date"], "price": exit_price,
                           "pnl%": pnl, "entry": entry_price})

    sells = [t for t in trades if t["type"] == "sell"]
    if not sells:
        return {"error": "无完整交易", "trades": 0}

    pnls = [t["pnl%"] for t in sells]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    cumulative = 0; max_cum = 0; max_dd = 0
    for p in pnls:
        cumulative += p; max_cum = max(max_cum, cumulative)
        max_dd = max(max_dd, cumulative - max_cum)
    cons = 0; max_cons = 0
    for p in pnls:
        cons = cons + 1 if p <= 0 else 0
        max_cons = max(max_cons, cons)

    return {
        "trades": len(sells),
        "win_rate": round(len(wins)/len(pnls)*100, 1),
        "avg_win": round(sum(wins)/len(wins), 2) if wins else 0,
        "avg_loss": round(sum(losses)/len(losses), 2) if losses else 0,
        "profit_factor": round(abs(sum(wins)/sum(losses)), 2) if losses and sum(losses)!=0 else 99,
        "total_return": round(sum(pnls), 2),
        "max_drawdown": round(max_dd, 2),
        "max_cons_loss": max_cons,
        "last5_pnls": [round(p,2) for p in pnls[-5:]] if len(pnls)>=5 else [round(p,2) for p in pnls],
    }

# ============================================================
# 策略定义
# ============================================================

STRATEGIES = {
    "保守策略 (MA20)": {
        "sell": [
            {"condition": lambda c: c["close"] < c["ma20"], "desc": "跌破MA20"},
            {"condition": lambda c: c["chg"] < -5 and c["vol_ratio"] > 2.0, "desc": "暴跌放量"},
        ],
        "buy": [
            {"condition": lambda c: c["close"] > c["ma10"] and c["ma10"] > c["ma20"] and c["vol_ratio"] > 1.0,
             "desc": "站上MA10+上升趋势"},
        ],
    },
    "优化策略 (MA10)": {
        "sell": [
            {"condition": lambda c: c["close"] < c["ma10"], "desc": "跌破MA10"},
            {"condition": lambda c: c["chg"] < -3 and c["vol_ratio"] > 1.5, "desc": "放量长阴"},
        ],
        "buy": [
            {"condition": lambda c: c["close"] > c["ma5"] and c["ma5"] > c["ma20"] and c["vol_ratio"] > 0.8,
             "desc": "站上MA5+多头排列"},
        ],
    },
    "基础策略 (MA5)": {
        "sell": [
            {"condition": lambda c: c["close"] < c["ma5"], "desc": "跌破MA5"},
            {"condition": lambda c: c["close"] < c["ma10"], "desc": "跌破MA10"},
            {"condition": lambda c: c["chg"] < -3 and c["vol_ratio"] > 1.5, "desc": "放量长阴"},
        ],
        "buy": [
            {"condition": lambda c: c["close"] > c["ma5"] and c["vol_ratio"] > 1.0, "desc": "站上MA5+放量"},
        ],
    },
}

# ============================================================
# AI 判定
# ============================================================

def ai_verdict(r):
    """根据回测结果生成 AI 可读判定"""
    if "error" in r: return {"verdict": "无效", "reason": r["error"], "gate4": "blocked"}
    
    issues = []
    if r["win_rate"] < 40: issues.append(f"胜率偏低({r['win_rate']}%)")
    if r["max_drawdown"] > 15: issues.append(f"最大回撤过大({r['max_drawdown']}%)")
    if r["max_cons_loss"] > 5: issues.append(f"连续亏损过多({r['max_cons_loss']}次)")
    if r["profit_factor"] < 1.5: issues.append(f"盈亏比不足({r['profit_factor']})")
    
    if not issues:
        verdict = "有效"
        gate4 = "passed"
        rec = "策略通过回测验证，闸门4放行，可进入实盘观察"
    elif len(issues) <= 1:
        verdict = "有瑕疵"
        gate4 = "warning"
        rec = f"策略基本有效但{issues[0]}，闸门4放行但需标注风险"
    else:
        verdict = "无效"
        gate4 = "blocked"
        rec = f"策略不通过: {'; '.join(issues)}。闸门4拦截，禁止实盘使用"
    
    return {
        "verdict": verdict,
        "gate4": gate4,
        "issues": issues,
        "recommendation": rec,
    }

# ============================================================
# 主入口
# ============================================================

def run_backtest(codes=None):
    if codes is None:
        codes = list(ETF_CODES.keys())
    
    results = []
    for code in codes:
        data = fetch_kline(code)
        strategies = []
        
        for sname, rules in STRATEGIES.items():
            r = backtest(data, rules)
            v = ai_verdict(r)
            strategies.append({"name": sname, **r, **v})
        
        # 找最优策略
        valid = [s for s in strategies if "error" not in s]
        best = max(valid, key=lambda s: s["total_return"]) if valid else None
        
        # 风险评估
        if best and best["gate4"] == "passed":
            risk = {"level": "低", "reason": f"最优策略({best['name']})胜率{best['win_rate']}%，盈亏比{best['profit_factor']}"}
        elif best:
            risk = {"level": "中", "reason": f"最优策略有瑕疵: {best.get('issues',['未知'])[0]}"}
        else:
            risk = {"level": "高", "reason": "无有效策略"}
        
        results.append({
            "code": code,
            "name": ETF_CODES[code],
            "data_range": {"from": data[0]["date"], "to": data[-1]["date"], "bars": len(data)},
            "strategies": strategies,
            "best_strategy": best["name"] if best else "无",
            "risk_assessment": risk,
        })
    
    # 综合判定
    blocked = sum(1 for r in results if r["risk_assessment"]["level"] == "高")
    warnings = sum(1 for r in results if r["risk_assessment"]["level"] == "中")
    
    if blocked == 0 and warnings == 0:
        overall = "✅ 全部策略通过回测，闸门4放行"
    elif blocked == 0:
        overall = f"⚠️ {warnings}只ETF策略有瑕疵，闸门4放行但需标注风险"
    else:
        overall = f"🔴 {blocked}只ETF策略被拦截，闸门4禁止相关策略实盘"

    return {
        "run_at": datetime.now().isoformat(),
        "results": results,
        "overall_verdict": overall,
        "action_items": [
            f"{r['code']} {r['name']}: {'通过' if r['risk_assessment']['level']=='低' else '需关注'}"
            for r in results
        ],
    }

def format_text(output):
    """人类可读输出"""
    print(f"\n{'='*65}")
    print(f"  ETF 策略回测报告 — {output['run_at'][:19]}")
    print(f"{'='*65}")
    
    for r in output["results"]:
        d = r["data_range"]
        print(f"\n── {r['code']} {r['name']} ({d['from']}~{d['to']}, {d['bars']}根)")
        for s in r["strategies"]:
            if "error" in s:
                print(f"  [{s['name']}] {s['error']}")
                continue
            g4 = "✅" if s["gate4"]=="passed" else "⚠️" if s["gate4"]=="warning" else "🔴"
            print(f"  {g4} [{s['name']}] {s['trades']}笔 胜率{s['win_rate']}% "
                  f"盈亏比{s['profit_factor']} 累计{s['total_return']:+.1f}% "
                  f"回撤-{s['max_drawdown']}%")
        
        ra = r["risk_assessment"]
        print(f"  📊 风险: {ra['level']} | {ra['reason']}")
    
    print(f"\n{'='*65}")
    print(f"  {output['overall_verdict']}")
    print(f"{'='*65}")

if __name__ == "__main__":
    use_json = "--json" in sys.argv
    codes = None
    for i, arg in enumerate(sys.argv):
        if arg == "--code" and i+1 < len(sys.argv):
            codes = [sys.argv[i+1]]

    output = run_backtest(codes)

    if use_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        format_text(output)
