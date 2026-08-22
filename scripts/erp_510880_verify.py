"""
510880 红利ETF — ERP策略可行性验证
========================================
对比4种策略在510880上的账户表现:
  1. 买入持有 (期初一次性)
  2. 机械定投 (每月固定B元, 不管ERP)
  3. ERP分档定投 (按ERP区间决定当月买入额: <5.5→0 / 5.5-6→1B / 6-6.5→1B / 6.5-7→1.5B / >=7→2B)
  4. ERP高档仅买 (只在ERP>=5.5%时买入1B, 符合用户挑买点风格)

数据: 510880真实单位净值(含分红=真全收益) + 沪深300 ERP
口径: 乐咕TTM PE (回测口径; 实盘需用中证静态校准刻度)
"""
import akshare as ak
import pandas as pd
import numpy as np
import warnings; warnings.filterwarnings('ignore')

print("=" * 72)
print("  510880 红利ETF — ERP策略可行性验证")
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
print(f"  ERP月度: {len(erp_m)} ({erp_m['日期'].min().date()} ~ {erp_m['日期'].max().date()})")

# 510880 月度净值
nav = ak.fund_open_fund_info_em(symbol="510880", period="全部")
nav = nav.rename(columns={"净值日期": "日期", "单位净值": "nav"})
nav["日期"] = pd.to_datetime(nav["日期"])
nav["ym"] = nav["日期"].dt.to_period("M")
nav_m = nav.groupby("ym", as_index=False).agg({"日期": "last", "nav": "last"})
print(f"  510880月度: {len(nav_m)} ({nav_m['日期'].min().date()} ~ {nav_m['日期'].max().date()})")

# 合并: 以510880存在的月份为准, left join ERP
nav_m = pd.merge(nav_m, erp_m[["ym", "erp"]], on="ym", how="left")
nav_m["ret"] = nav_m["nav"].pct_change().fillna(0)
nav_m = nav_m.dropna(subset=["erp"]).reset_index(drop=True)
print(f"  合并后(有ERP的月份): {len(nav_m)} ({nav_m['日期'].min().date()} ~ {nav_m['日期'].max().date()})")

# ============ 2. 策略模拟函数 ============
def simulate(nav_m, invest_func, B=3000.0):
    """每月末按 invest_func(erp) 决定当月投入金额, 下月初买入."""
    cash = 0.0
    shares = 0.0
    invested = 0.0
    for i in range(len(nav_m)):
        amt = invest_func(nav_m["erp"].iloc[i])
        if amt > 0 and i + 1 < len(nav_m):
            price = nav_m["nav"].iloc[i]  # 当月净值买入
            shares += amt / price
            invested += amt
    final_nav = nav_m["nav"].iloc[-1]
    market_val = shares * final_nav
    total_ret = (market_val / invested - 1) * 100 if invested > 0 else 0
    # 总投资月
    n_months = len(nav_m)
    years = n_months / 12
    annual = ((market_val / invested) ** (1/years) - 1) * 100 if invested > 0 else 0
    return invested, market_val, total_ret, annual

def max_drawdown(nav_close):
    """基于净值序列的最大回撤 - 用基准价格."""
    peak = -np.inf
    mdd = 0
    for v in nav_close:
        if v > peak: peak = v
        dd = (peak - v) / peak
        if dd > mdd: mdd = dd
    return mdd * 100

# 基准回撤（每月末净值）
nav_series = nav_m["nav"].values

# ============ 3. 四种策略 ============
print("\n[2] 四种策略对比 (B=3000元/单位)")
print("-" * 72)

# 策略参数 - 用ERP>=2015年后较准确的月份 (乐咕PE 2015后准)

# a. 机械定投 (每月固定3000)
invested_fixed, mv_fixed, ret_fixed, ann_fixed = simulate(nav_m, lambda erp: 3000.0 if not np.isnan(erp) else 0)

# b. ERP分档定投
def band(erp):
    if np.isnan(erp): return 0
    if erp < 5.5: return 0
    if erp < 6.5: return 3000.0   # 5.5-6.5 → 1B
    if erp < 7.0: return 4500.0   # 6.5-7 → 1.5B
    return 6000.0                  # >=7 → 2B
invested_band, mv_band, ret_band, ann_band = simulate(nav_m, band)

# c. ERP高档仅买 (只在>=5.5%买1B)
invested_hi, mv_hi, ret_hi, ann_hi = simulate(nav_m, lambda erp: 3000.0 if (not np.isnan(erp) and erp >= 5.5) else 0)

# d. 买入持有 (期初一次性投入 = 机械定投总投资额, 公平对比)
# 用机械定投累计投入相同的钱一次性买入
total_cap = invested_fixed
first_nav = nav_m["nav"].iloc[0]
last_nav = nav_m["nav"].iloc[-1]
ret_bh = (last_nav / first_nav - 1) * 100
ann_bh = ((last_nav/first_nav)**(12/len(nav_m))-1)*100

print(f"{'策略':<16}{'累计投入':>10}{'期末市值':>10}{'累计收益%':>10}{'年化%':>8}")
print("-" * 62)
print(f"{'买入持有':<14}{total_cap:>10.0f}{total_cap*(1+ret_bh/100):>10.0f}{ret_bh:>10.1f}{ann_bh:>8.2f}")
print(f"{'机械定投':<14}{invested_fixed:>10.0f}{mv_fixed:>10.0f}{ret_fixed:>10.1f}{ann_fixed:>8.2f}")
print(f"{'ERP分档定投':<14}{invested_band:>10.0f}{mv_band:>10.0f}{ret_band:>10.1f}{ann_band:>8.2f}")
print(f"{'ERP高档仅买':<14}{invested_hi:>10.0f}{mv_hi:>10.0f}{ret_hi:>10.1f}{ann_hi:>8.2f}")

# ============ 4. 买入时点分布 ============
print("\n[3] ERP分档: 买入次数分布")
print("-" * 50)
n_55 = sum(1 for e in nav_m["erp"] if 5.5 <= e < 6.5)
n_65 = sum(1 for e in nav_m["erp"] if 6.5 <= e < 7.0)
n_70 = sum(1 for e in nav_m["erp"] if e >= 7.0)
print(f"  ERP 5.5-6.5% 买入月: {n_55} 次")
print(f"  ERP 6.5-7%  买入月: {n_65} 次")
print(f"  ERP >=7%    买入月: {n_70} 次")
print(f"  总计触发买入: {n_55+n_65+n_70} / {len(nav_m)} 月")

# ============ 5. 分档未来12月收益 ============
print("\n[4] 510880 各ERP档 — 未来12个月表现")
print("-" * 60)
th = [(0,3,'<3%'),(3,4,'3-4%'),(4,5,'4-5%'),(5,5.5,'5-5.5%'),(5.5,6,'5.5-6%'),(6,6.5,'6-6.5%'),(6.5,7,'6.5-7%'),(7,20,'>=7%')]
print(f"{'档位':<10}{'样本':>6}{'12月胜率':>10}{'12月均收益':>12}{'12月最差':>10}")
for low, high, label in th:
    mask = (nav_m["erp"] >= low) & (nav_m["erp"] < high)
    idx = np.where(mask)[0]
    recs = []
    for i in idx:
        f = nav_m["ret"].iloc[i+1:i+13]
        if len(f) == 12 and not f.isna().any():
            recs.append((1+f).prod()-1)
    if len(recs) >= 3:
        recs = np.array(recs)
        print(f"{label:<10}{len(recs):>6}{np.mean(recs>0)*100:>9.0f}%{np.mean(recs)*100:>11.1f}%{recs.min()*100:>9.1f}%")
    else:
        print(f"{label:<10}{len(recs):>6}{'样本不足':>10}")

# ============ 6. 当前状态 ============
print("\n[5] 当前状态")
last = nav_m.iloc[-1]
print(f"  日期: {last['日期'].date()}")
print(f"  510880净值: {last['nav']:.3f}")
print(f"  当前ERP: {last['erp']:.2f}%")
if last["erp"] >= 7: print("  → 极强定投区 (2B)")
elif last["erp"] >= 6.5: print("  → 强定投区 (1.5B)")
elif last["erp"] >= 5.5: print("  → 可选定投区 (1B)")
else: print("  → WAIT区 (不建议主动买入)")

print("\n" + "=" * 72)
print("  结论见上方综合分析")
print("=" * 72)