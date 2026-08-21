"""
ERP 分档定投回测 (按用户 v2 设计)
========================================
信号: 沪深300 ERP (用 TTM PE)
标的: 515080 中证红利ETF (用中证红利全收益指数作历史代理)
规则: 月末观察 ERP → 下月决策 → 多档位购买
"""

import akshare as ak
import pandas as pd
import numpy as np

print("=" * 75)
print("  ERP 分档定投策略回测 (用户v2)")
print("=" * 75)

# ============================================================
# 1. 数据获取
# ============================================================
print("\n[1] 拉取数据 ...")

# 沪深300 PE (乐咕乐股，从2005)
pe_df = ak.stock_index_pe_lg(symbol="沪深300")
pe_df["日期"] = pd.to_datetime(pe_df["日期"])
pe_df = pe_df[["日期", "指数", "滚动市盈率"]].rename(
    columns={"指数": "idx300", "滚动市盈率": "pe300_ttm"}
)

# 10年期国债 (AkShare)
bond_df = ak.bond_zh_us_rate()
bond_df["日期"] = pd.to_datetime(bond_df["日期"])
bond_df = bond_df[["日期", "中国国债收益率10年"]].rename(columns={"中国国债收益率10年": "y10"})

# B方案: 红利数据 — 515080 ETF 单位净值 (含分红再投资, 真全收益)
try:
    red_df = ak.fund_open_fund_info_em(symbol="515080", period="10y")
    red_df = red_df.rename(columns={"净值日期": "日期", "单位净值": "red_close"})
    red_df["日期"] = pd.to_datetime(red_df["日期"])
    red_df = red_df[["日期", "red_close"]]
    proxy_mode = "515080 ETF单位净值(含分红, 2019.12~)"
except Exception as e:
    print(f"515080 ETF失败: {e}")
    red_df = pd.DataFrame()
    proxy_mode = "失败"

print(f"  沪深300 PE: {len(pe_df)} 条")
print(f"  10Y国债: {len(bond_df)} 条")
print(f"  红利代理: {len(red_df)} 条 ({proxy_mode})")

# ============================================================
# 2. 合并 + 计算 ERP
# ============================================================
print("\n[2] 合并 + 计算 ERP ...")
df = pd.merge(pe_df, bond_df, on="日期", how="inner").sort_values("日期")
df["ey"] = 100 / df["pe300_ttm"]  # 盈利收益率
df["erp"] = df["ey"] - df["y10"]   # 股债利差

# 月末采样
df["ym"] = df["日期"].dt.to_period("M")
m = df.groupby("ym", as_index=False).agg({"日期": "last", "idx300": "last",
                          "pe300_ttm": "last", "y10": "last", "erp": "last"})

print(f"  月度样本: {len(m)} 个 ({m['日期'].min().date()} ~ {m['日期'].max().date()})")

# 红利数据月度对齐 (不丢ERP月份)
if len(red_df):
    red_df["ym"] = red_df["日期"].dt.to_period("M")
    red_m = red_df.groupby("ym", as_index=False).agg({"日期": "last", "red_close": "last"})
    red_m["red_ret"] = red_m["red_close"].pct_change().fillna(0)

    # 合并：ERP 全部，红利用 left join 保持 ERP 月份不丢
    m = pd.merge(m[["日期", "ym", "erp", "pe300_ttm", "y10"]],
                 red_m[["ym", "red_close", "red_ret"]], on="ym", how="left")
else:
    m["red_ret"] = np.nan

# ============================================================
# 3. 分档统计 - 未来 N 月收益
# ============================================================
print("\n[3] 分档统计 (买入后未来N个月表现)")

def future_stats(ret_series, erp_series, n, thresholds):
    rows = []
    for low, high, label in thresholds:
        mask = (erp_series >= low) & (erp_series < high)
        idx = np.where(mask)[0]
        records = []
        for i in idx:
            # 要求未来N月都有收益数据
            future = ret_series.iloc[i+1:i+1+n]
            if len(future) == n and not future.isna().any():
                cumret = (1 + future).prod() - 1
                records.append(cumret)
        if len(records):
            records = np.array(records)
            win_rate = (records > 0).mean() * 100
            avg = records.mean() * 100
            worst = records.min() * 100
            rows.append([label, len(records), win_rate, avg, worst])
        else:
            rows.append([label, 0, np.nan, np.nan, np.nan])
    return pd.DataFrame(rows, columns=["ERP区间", "样本月", "胜率%", "平均收益%", "最差收益%"])

thresholds = [
    (0, 3, "<3%"), (3, 4, "3-4%"), (4, 5, "4-5%"),
    (5, 5.5, "5-5.5%"), (5.5, 6, "5.5-6%"), (6, 6.5, "6-6.5%"),
    (6.5, 7, "6.5-7%"), (7, 20, ">=7%"),
]

if "red_ret" in m.columns and m["red_ret"].sum() != 0:
    print("\n  === 未来6/12个月表现 (中证红利代理) ===")
    for n in [6, 12, 24]:
        print(f"\n  未来{n}个月:")
        stats = future_stats(m["red_ret"], m["erp"], n, thresholds)
        print(stats.to_string(index=False))

# 单笔资金 IRR (考虑时间价值)
print("\n[4] 单笔资金 IRR (考虑持有期, 几何年化)")

# 对每个 ERP 阈值, 计算实际投入资金的"加权平均年化收益率"
buy_thresholds = [0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0]
irrs = []
for buy_th in buy_thresholds:
    # 找出所有买入月份 (ERP 满足) 且有未来收益数据
    eligible_idx = [i for i in range(len(m))
                     if m["erp"].iloc[i] >= buy_th
                     and i + 12 < len(m)
                     and not m["red_ret"].iloc[i+1:i+13].isna().any()]

    if len(eligible_idx) < 12:
        irrs.append([f">={buy_th}%", len(eligible_idx), np.nan, np.nan])
        continue

    # 12个月窗口的算术平均 (实际收益表现)
    avg_12m_return = np.mean([(1 + m["red_ret"].iloc[i+1:i+13]).prod() - 1
                               for i in eligible_idx]) * 100
    # 月度滚动 IRR 估算 (12个月持有期)
    monthly_total = np.mean([(1 + m["red_ret"].iloc[i+1:i+2]).prod() - 1
                              for i in eligible_idx]) * 100  # 单月均值
    annual_irr = ((1 + avg_12m_return/100) ** (12/12) - 1) * 100  # 12月持有IRR
    # 用月度几何平均外推年化 (适合长期定投视角)
    month_factor = 1.0
    for i in eligible_idx[:24]:  # 前24次买入
        r = m["red_ret"].iloc[i+1]
        if not np.isnan(r):
            month_factor *= (1 + r)
    n = min(24, len(eligible_idx))
    geo_annual = (month_factor ** (12/n) - 1) * 100 if n > 0 else np.nan

    irrs.append([f">={buy_th}%", len(eligible_idx), avg_12m_return, geo_annual])

df_irr = pd.DataFrame(irrs, columns=["买入条件", "实际买入月", "12月平均收益%", "几何年化IRR%"])
print(df_irr.to_string(index=False, float_format=lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A"))

# ============================================================
# 5. 当前状态
# ============================================================
print("\n" + "=" * 75)
print("  当前状态 (最新月度样本)")
print("=" * 75)
last = m.iloc[-1]
print(f"  日期: {last['日期'].date()}")
print(f"  沪深300 PE-TTM: {last['pe300_ttm']:.2f}")
print(f"  10Y国债: {last['y10']:.4f}%")
print(f"  ERP: {last['erp']:.2f}%")

# 历史分位
hist_pct = (m["erp"] <= last["erp"]).mean() * 100
print(f"  历史分位: {hist_pct:.1f}% (中位数={m['erp'].median():.2f}%)")

# 决策
erp_now = last["erp"]
if erp_now < 5.0:
    decision = "🟡 WAIT (不主动买入)"
elif erp_now < 5.5:
    decision = "🟡 观察区 (5.0-5.5%) - 仅红利自身便宜才试探 0.5B"
elif erp_now < 6.0:
    decision = "🟢 轻度定投 (5.5-6.0%) - 1B"
elif erp_now < 6.5:
    decision = "🟢 正常定投 (6.0-6.5%) - 1B"
elif erp_now < 7.0:
    decision = "🟢 强定投 (6.5-7.0%) - 1.5B"
else:
    decision = "🟢 极强定投 (≥7.0%) - 2B"

print(f"\n  📌 当前决策: {decision}")

# ============================================================
# 6. 输出5档建议
# ============================================================
print("\n" + "=" * 75)
print("  最终建议 (按用户v2设计)")
print("=" * 75)
print(f"""
{'沪深300 ERP':<14} {'历史状态':<10} {'基础动作':<22} {'B=3000元':>10}
{'-'*60}
{'<5.0%':<14} {'一般/昂贵':<10} {'不买 (WAIT)':<22} {'0元':>10}
{'5.0–5.5%':<14} {'观察':<10} {'仅红利便宜时试买':<22} {'0~1500元':>10}
{'5.5–6.0%':<14} {'有吸引力':<10} {'轻度定投':<22} {'1500元':>10}
{'6.0–6.5%':<14} {'明显便宜':<10} {'正常定投':<22} {'3000元':>10}
{'6.5–7.0%':<14} {'很便宜':<10} {'强定投':<22} {'4500元':>10}
{'≥7.0%':<14} {'极端机会':<10} {'极强定投':<22} {'6000元':>10}

红利自身过滤器:
  • 中证红利 PE便宜 + 股息率利差高 → 保持原档位
  • 中证红利自身估值一般 → 下降一级
  • 中证红利明显昂贵 → 下降两级
""")