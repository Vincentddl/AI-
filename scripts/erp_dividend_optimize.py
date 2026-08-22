"""
ERP 分档定投 — 主流红利指数优化回测
========================================
评估: 当前策略(标的515080中证红利 + ERP分档定投)是否有优化空间?
对比 5 只主流红利 ETF 在相同 ERP 分档下的表现,
检验当前标的 vs 替换标的、以及各档位收益差。

口径: 乐咕TTM PE (唯一有长历史的回测口径) — 结论看相对排序, 绝对阈值需实盘校准
"""
import akshare as ak
import pandas as pd
import numpy as np

print("=" * 78)
print("  主流红利指数 × ERP分档定投 — 优化空间回测")
print("  当前策略: 515080中证红利 + ERP分档(5.5-6%→1B/6-6.5%→1B/6.5-7%→1.5B/≥7%→2B)")
print("=" * 78)

# ============================================================
# 1. 加载沪深300 ERP 信号
# ============================================================
print("\n[1] 加载沪深300 ERP信号 (乐咕TTM PE)")
pe = ak.stock_index_pe_lg(symbol="沪深300")
pe["日期"] = pd.to_datetime(pe["日期"])
bond = ak.bond_zh_us_rate()
bond["日期"] = pd.to_datetime(bond["日期"])
bond = bond[["日期", "中国国债收益率10年"]].rename(columns={"中国国债收益率10年": "y10"})
merged = pd.merge(pe[["日期", "滚动市盈率"]], bond, on="日期", how="inner")
merged["erp"] = 100 / merged["滚动市盈率"] - merged["y10"]
merged["ym"] = merged["日期"].dt.to_period("M")
erp_m = merged.groupby("ym", as_index=False).agg({"日期": "last", "erp": "last"})
print(f"  ERP月度样本: {len(erp_m)} 个 ({erp_m['日期'].min().date()} ~ {erp_m['日期'].max().date()})")

# ============================================================
# 2. 加载候选红利 ETF 净值 (含分红=真全收益)
# ============================================================
print("\n[2] 加载主流红利ETF单位净值")
candidates = [
    ("510880", "红利ETF", "中证红利"),
    ("512890", "红利低波ETF", "红利低波"),
    ("515080", "中证红利ETF★当前", "中证红利"),
    ("515100", "红利低波100", "红利低波100"),
    ("159631", "红利质量", "红利质量"),
]

navs = {}
for code, name, idx in candidates:
    try:
        df = ak.fund_open_fund_info_em(symbol=code, period="10y")
        df = df.rename(columns={"净值日期": "日期", "单位净值": "nav"})
        df["日期"] = pd.to_datetime(df["日期"])
        df["ym"] = df["日期"].dt.to_period("M")
        d = df.groupby("ym", as_index=False).agg({"日期": "last", "nav": "last"})
        d["ret"] = d["nav"].pct_change().fillna(0)
        navs[code] = {"name": name, "idx": idx, "df": d}
        print(f"  {code} {name:12s}: {len(d):4d}月 | {d['日期'].min().date()} ~ {d['日期'].max().date()}")
    except Exception as e:
        print(f"  {code} {name}: 失败 {str(e)[:60]}")

# ============================================================
# 3. ERP 分档 × 未来12个月收益 (按标的)
# ============================================================
print("\n" + "=" * 78)
print("  A. 各EOF ERP分档 — 未来12个月平均收益 (判断哪个标的最优)")
print("=" * 78)
thresholds = [
    (0, 3, "<3%"), (3, 4, "3-4%"), (4, 5, "4-5%"),
    (5, 5.5, "5-5.5%"), (5.5, 6, "5.5-6%"), (6, 6.5, "6-6.5%"),
    (6.5, 7, "6.5-7%"), (7, 20, ">=7%"),
]

def future_12(erp_sig, ret_sig, low, high):
    mask = (erp_sig >= low) & (erp_sig < high)
    idx = np.where(mask)[0]
    recs = []
    for i in idx:
        f = ret_sig.iloc[i+1:i+13]
        if len(f) == 12 and not f.isna().any():
            recs.append((1 + f).prod() - 1)
    if len(recs) >= 3:
        return len(recs), np.mean(recs) * 100, np.mean([r > 0 for r in recs]) * 100
    return 0, np.nan, np.nan

# 汇总各标的各档位
summary = {}
for code, info in navs.items():
    d = info["df"]
    m2 = pd.merge(erp_m[["ym", "erp"]], d[["ym", "ret"]], on="ym", how="inner")
    row = {}
    for low, high, label in thresholds:
        n, avg, win = future_12(m2["erp"], m2["ret"], low, high)
        row[label] = (n, avg, win)
    summary[code] = {"name": info["name"], "row": row}

# 打印
hdr = "ETF" + " " * 8 + "样本"
for label in [t[2] for t in thresholds]:
    hdr += f"  {label:>10}"
print(hdr)
print("-" * 120)
for code, info in summary.items():
    line = f"{code} {info['name']:10s} {len(navs[code]['df']):4d}"
    for low, high, label in thresholds:
        n, avg, win = info["row"][label]
        if n:
            line += f"  {win:3.0f}%{avg:>6.1f}"
        else:
            line += "  " + " " * 9
    print(line)

# ============================================================
# 4. 当前策略 vs 优化: 只买 >=5.5% 档位 (用户挑买点风格)
# ============================================================
print("\n" + "=" * 78)
print("  B. 当前策略实测: 只在 ERP>=5.5% 买入 (用户偏好挑买点), 各标的对比")
print("=" * 78)
print(f"{'ETF':<18}{'触发买入月':<10}{'平均12月收益%':>14}{'胜率%':>10}{'InfoRatio':>10}")
print("-" * 70)

buy_low = 5.5  # 只在 ERP >= 5.5% 买入
scores = []
for code, info in navs.items():
    d = info["df"]
    m2 = pd.merge(erp_m[["ym", "erp"]], d[["ym", "ret"]], on="ym", how="inner")
    m2 = m2.reset_index(drop=True)
    mask = m2["erp"] >= buy_low
    idx = np.where(mask)[0]
    recs = []
    for i in idx:
        f = m2["ret"].iloc[i+1:i+13]
        if len(f) == 12 and not f.isna().any():
            recs.append((1 + f).prod() - 1)
    if len(recs) >= 12:
        recs = np.array(recs)
        avg = recs.mean() * 100
        win = (recs > 0).mean() * 100
        std = recs.std() * 100
        ir = avg / std if std > 0 else np.nan
        scores.append((code, info["name"], len(recs), avg, win, ir))
    else:
        scores.append((code, info["name"], len(recs), np.nan, np.nan, np.nan))

scores.sort(key=lambda x: -(x[3] if not np.isnan(x[3]) else -999))
for code, name, n, avg, win, ir in scores:
    star = "★" if code == "515080" else " "
    print(f"{code} {name}{star:<9}{n:<10}{avg:>13.1f}{win:>10.1f}{ir:>10.2f}")

# ============================================================
# 5. 总账户 IRR: 分档资金再平衡 (真实投入回报)
# ============================================================
print("\n" + "=" * 78)
print("  C. 总账户IRR — 分档金额策略 (含现金闲置成本)")
print("=" * 78)
# 分档: ERP<5.5→0, 5.5-6→1B, 6-6.5→1B, 6.5-7→1.5B, >=7→2B (B=1单位=3000)
def band_amount(erp):
    if erp < 5.5: return 0
    if erp < 6.5: return 1.0
    if erp < 7.0: return 1.5
    return 2.0

# 对每个标的总账户模拟: 月末定投B元, 遇到好档位加大
print(f"\n  {'ETF':<18}{'累计投入':>10}{'期末市值':>10}{'总账户IRR%':>12}{'max回撤%':>10}")
for code, info in navs.items():
    d = info["df"]
    m2 = pd.merge(erp_m[["ym", "erp"]], d[["ym", "ret"]], on="ym", how="inner").reset_index(drop=True)
    # 资产模拟 (单位账户, B=3000固定每月都可投, 但实际只在>=5.5投)
    cash = 0.0
    shares = 0.0
    invested = 0.0
    nav_last = None
    peaks = []
    for i, r in m2.iterrows():
        amt = band_amount(r["erp"]) * 3000
        # 用下月收益: 本月投入, 下月开始产生收益
        if i < len(m2) - 1 and amt > 0:
            shares += amt / d["nav"].iloc[max(0, i)]  # 当月净值买入
            invested += amt
    # 评估期末
    final_nav = d["nav"].iloc[-1]
    market_val = shares * final_nav
    if invested > 0:
        total_irr = (market_val / invested - 1) * 100 if invested else 0
        print(f"  {code} {info['name']:<12}{invested:>10.0f}{market_val:>10.0f}{total_irr:>12.1f}")

print("\n" + "=" * 78)
print("  优化空间结论 (见上方综合分析)")
print("=" * 78)