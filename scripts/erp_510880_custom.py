"""
510880 红利ETF — 专属ERP档位规则 vs 原版规则
========================================
定制版: 压中间档(6-6.5%特弱)、重仓>=7%(胜率96%/+37%)
对比: 原版通用档位 vs 定制版(510880专属)
数据: 510880真实单位净值(含分红全收益, 2006~2026) + 沪深300 ERP
"""
import akshare as ak
import pandas as pd
import numpy as np
import warnings; warnings.filterwarnings('ignore')

print("=" * 72)
print("  510880 红利ETF — 专属ERP档位优化回测")
print("=" * 72)

# ============ 1. 数据 ============
print("\n[1] 拉取数据 ...")
pe = ak.stock_index_pe_lg(symbol="沪深300")
pe["日期"] = pd.to_datetime(pe["日期"])
bond = ak.bond_zh_us_rate()
bond["日期"] = pd.to_datetime(bond["日期"])
bond = bond[["日期", "中国国债收益率10年"]].rename(columns={"中国国债收益率10年": "y10"})
merged = pd.merge(pe[["日期", "滚动市盈率"]], bond, on="日期", how="inner")
merged["erp"] = 100 / merged["滚动市盈率"] - merged["y10"]
merged["ym"] = merged["日期"].dt.to_period("M")
erp_m = merged.groupby("ym", as_index=False).agg({"日期": "last", "erp": "last"})

nav = ak.fund_open_fund_info_em(symbol="510880", period="全部")
nav = nav.rename(columns={"净值日期": "日期", "单位净值": "nav"})
nav["日期"] = pd.to_datetime(nav["日期"])
nav["ym"] = nav["日期"].dt.to_period("M")
nav_m = nav.groupby("ym", as_index=False).agg({"日期": "last", "nav": "last"})
nav_m = pd.merge(nav_m, erp_m[["ym", "erp"]], on="ym", how="left")
nav_m["ret"] = nav_m["nav"].pct_change().fillna(0)
nav_m = nav_m.dropna(subset=["erp"]).reset_index(drop=True)
print(f"  510880月度(含ERP): {len(nav_m)} ({nav_m['日期'].min().date()} ~ {nav_m['日期'].max().date()})")

# ============ 2. 策略模拟: 返回每月的持仓市值曲线(算回撤) ============
def simulate_full(nav_m, invest_func, B=3000.0):
    shares = 0.0
    invested = 0.0
    dates = []
    mkt_vals = []
    buy_months = []
    single_returns = []  # 每笔买入后12月收益
    for i in range(len(nav_m)):
        erp = nav_m["erp"].iloc[i]
        amt = invest_func(erp)
        dates.append(nav_m["日期"].iloc[i])
        if amt > 0:
            price = nav_m["nav"].iloc[i]
            shares += amt / price
            invested += amt
            buy_months.append(i)
            # 单笔未来12月收益
            f = nav_m["ret"].iloc[i+1:i+13]
            if len(f) == 12 and not f.isna().any():
                single_returns.append((1+f).prod()-1)
        mkt_vals.append(shares * nav_m["nav"].iloc[i])
    vals = pd.Series(mkt_vals, index=dates)
    # 最大回撤
    peak = vals.cummax()
    dd = (vals - peak) / peak
    mdd = dd.min() * 100
    final_nav = nav_m["nav"].iloc[-1]
    market_val = shares * final_nav
    # 资金时间价值 IRR (XIRR近似, 月IRR二分法, 纯numpy)
    t0 = dates[0]
    def npv(r_month):
        total = market_val
        for k in range(len(nav_m)):
            amt = invest_func(nav_m["erp"].iloc[k])
            if amt > 0:
                months = (dates[k] - t0).days / 30.44
                total += -amt * (1 + r_month) ** (-months)
        return total
    lo, hi = -0.5, 3.0
    f_lo = npv(lo)
    for _ in range(100):
        mid = (lo + hi) / 2
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    monthly_irr = (lo + hi) / 2
    annual_irr = (1 + monthly_irr) ** 12 - 1
    avg12 = np.mean(single_returns)*100 if single_returns else np.nan
    win12 = np.mean([r>0 for r in single_returns])*100 if single_returns else np.nan
    return {
        "invested": invested, "market_val": market_val,
        "total_ret": (market_val/invested-1)*100,
        "annual_irr": annual_irr*100,
        "mdd": mdd, "n_buy": len(buy_months),
        "avg12": avg12, "win12": win12
    }

# ---- 原版通用档位 ----
def orig(erp):
    if erp < 5.5: return 0
    if erp < 6.5: return 3000.0
    if erp < 7.0: return 4500.0
    return 6000.0

# ---- 定制版(510880专属): 压6-6.5%特弱档, 重仓>=7% ----
def custom(erp):
    if erp < 5.5: return 0                       # WAIT
    if erp < 6.0: return 1500.0                  # 5.5-6 → 0.5B (80%胜率,试探)
    if erp < 6.5: return 1500.0                  # 6-6.5 → 0.5B (68%胜率,+1.4%特弱,压低)
    if erp < 7.0: return 3000.0                  # 6.5-7 → 1B (67%,+5%)
    return 9000.0                                # >=7 → 3B (96%胜率,+37%,重仓!)

# ---- 对比 ----
print("\n[2] 策略对比 (B=3000元)")
print("-" * 78)
r_orig = simulate_full(nav_m, orig)
r_cust = simulate_full(nav_m, custom)
print(f"{'指标':<14}{'原版通用档位':>18}{'定制版(重仓7)':>18}{'差异':>12}")
print("-" * 78)
metrics = [
    ("累计投入", lambda r: r["invested"]),
    ("期末市值", lambda r: r["market_val"]),
    ("累计收益%", lambda r: r["total_ret"]),
    ("年化IRR%", lambda r: r["annual_irr"]),
    ("最大回撤%", lambda r: r["mdd"]),
    ("买入次数", lambda r: r["n_buy"]),
    ("单笔12月均收益%", lambda r: r["avg12"]),
    ("单笔12月胜率%", lambda r: r["win12"]),
]
for name, f in metrics:
    a = f(r_orig); b = f(r_cust)
    diff = b - a if name not in ("期末市值","累计投入") else b/a*100-100
    dfmt = f"{diff:+.1f}" if abs(diff) > 1 else f"{diff:+.1f}"
    print(f"{name:<14}{a:>18.1f}{b:>18.1f}{'' if name=='买入次数' else dfmt:>12}")

# 买入次数单独显示
print(f"{'买入次数':<14}{r_orig['n_buy']:>18}{r_cust['n_buy']:>18}")

# ============ 3. 分档投入分布 ============
print("\n[3] 定制版买入分布")
print("-" * 50)
for label, lo, hi, amt in [("5.5-6%",5.5,6,1500),("6-6.5%",6,6.5,1500),("6.5-7%",6.5,7,3000),(">=7%",7,20,9000)]:
    n = sum(1 for e in nav_m["erp"] if lo <= e < hi)
    tot = n*amt
    print(f"  {label:<8} 触发{n:>3}次 × {amt:>5}元 = {tot:>8}元")

print("\n[4] 各档未来12月收益(回顾事实)")
print("-" * 60)
th = [(5.5,6,'5.5-6%'),(6,6.5,'6-6.5%'),(6.5,7,'6.5-7%'),(7,20,'>=7%')]
for lo, hi, label in th:
    mask = (nav_m["erp"] >= lo) & (nav_m["erp"] < hi)
    idx = np.where(mask)[0]
    recs = []
    for i in idx:
        f = nav_m["ret"].iloc[i+1:i+13]
        if len(f)==12 and not f.isna().any(): recs.append((1+f).prod()-1)
    if recs:
        recs = np.array(recs)
        print(f"  {label:<10}样本{len(recs):>3} | 胜率{np.mean(recs>0)*100:>4.0f}% | 均收益{np.mean(recs)*100:>6.1f}% | 最差{recs.min()*100:>6.1f}%")

# ============ 4. 当前状态 ============
print("\n[5] 当前状态 (2026-08)")
last = nav_m.iloc[-1]
print(f"  510880净值 {last['nav']:.3f} | 当前ERP {last['erp']:.2f}%")
if last["erp"] >= 7: print("  → 定制版: 重仓区 (3B/n月)")
elif last["erp"] >= 6.5: print("  → 定制版: 正常区 (1B)")
elif last["erp"] >= 6: print("  → 定制版: 试探区 (0.5B, 因该档收益特弱)")
elif last["erp"] >= 5.5: print("  → 定制版: 试探区 (0.5B)")
else: print("  → 定制版: WAIT区 (不买)")

print("\n" + "=" * 72)