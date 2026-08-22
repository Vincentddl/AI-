"""
多只红利ETF回测对比
========================================
比较 5 只主流红利 ETF 在 ERP 估值择时下的表现
"""

import akshare as ak
import pandas as pd
import numpy as np

print("=" * 80)
print("  红利ETF ERP估值定投 — 多产品回测对比")
print("=" * 80)

# ============================================================
# 1. 候选 ETF
# ============================================================
candidates = [
    # 红利型 (主流A股, 成交额前3, 历史长)
    ("512890", "红利低波ETF", "红利"),
    ("510880", "红利ETF", "红利"),
    ("515080", "中证红利ETF", "红利"),
    # 自由现金流型 (主流, 成交额前3, 但历史短)
    ("159232", "自由现金流ETF南方", "自由现金流"),
    ("159201", "自由现金流ETF华夏", "自由现金流"),
    ("159399", "现金流ETF国泰", "自由现金流"),
]

# ============================================================
# 2. 加载沪深300 ERP 信号
# ============================================================
print("\n[1] 加载沪深300 ERP 信号 ...")
pe_df = ak.stock_index_pe_lg(symbol="沪深300")
pe_df["日期"] = pd.to_datetime(pe_df["日期"])
bond_df = ak.bond_zh_us_rate()
bond_df["日期"] = pd.to_datetime(bond_df["日期"])
bond_df = bond_df[["日期", "中国国债收益率10年"]].rename(columns={"中国国债收益率10年": "y10"})

merged = pd.merge(pe_df[["日期", "滚动市盈率"]], bond_df, on="日期", how="inner")
merged["erp"] = 100 / merged["滚动市盈率"] - merged["y10"]

# 月度采样
merged["ym"] = merged["日期"].dt.to_period("M")
erp_monthly = merged.groupby("ym", as_index=False).agg(
    {"日期": "last", "erp": "last"}
)
print(f"  ERP月度样本: {len(erp_monthly)} 个 ({erp_monthly['日期'].min().date()} ~ {erp_monthly['日期'].max().date()})")

# ============================================================
# 3. 加载每只 ETF 的月度收益
# ============================================================
print("\n[2] 加载 ETF 单位净值 ...")

results = {}
for code, name, idx in candidates:
    try:
        nav = ak.fund_open_fund_info_em(symbol=code, period="10y")
        nav = nav.rename(columns={"净值日期": "日期", "单位净值": "nav"})
        nav["日期"] = pd.to_datetime(nav["日期"])
        nav["ym"] = nav["日期"].dt.to_period("M")
        nav = nav.groupby("ym", as_index=False).agg({"日期": "last", "nav": "last"})
        nav["ret"] = nav["nav"].pct_change().fillna(0)
        results[code] = {"name": name, "idx": idx, "data": nav}
        print(f"  {code} {name:14s}: {len(nav):4d}月 | {nav['日期'].min().date()} ~ {nav['日期'].max().date()}")
    except Exception as e:
        print(f"  {code} {name}: 失败 {str(e)[:80]}")

# ============================================================
# 4. ERP分档对比 — 未来 12 个月收益
# ============================================================
print("\n" + "=" * 80)
print("  ERP分档 — 未来12个月平均收益 (按产品)")
print("=" * 80)

# 用各ETF实际数据范围限制ERP样本
thresholds = [
    (0, 3, "<3%"), (3, 4, "3-4%"), (4, 5, "4-5%"),
    (5, 5.5, "5-5.5%"), (5.5, 6, "5.5-6%"), (6, 6.5, "6-6.5%"),
    (6.5, 7, "6.5-7%"), (7, 20, ">=7%"),
]

# 构建对比表
comparison_data = {}
for code, info in results.items():
    name = info["name"]
    df = info["data"]
    # 合并 ETF 月度收益 + ERP信号
    merged_etf = pd.merge(erp_monthly[["ym", "erp"]], df[["ym", "ret"]],
                           on="ym", how="inner")

    # 12月窗口统计
    row = {"成分股样本": len(df), "起始日期": df['日期'].min().date()}
    for low, high, label in thresholds:
        mask = (merged_etf["erp"] >= low) & (merged_etf["erp"] < high)
        idx = np.where(mask)[0]
        records = []
        for i in idx:
            future = merged_etf["ret"].iloc[i+1:i+13]
            if len(future) == 12 and not future.isna().any():
                records.append((1 + future).prod() - 1)
        if len(records) >= 3:
            row[f"{label}_胜率"] = f"{np.mean([r>0 for r in records])*100:.0f}%"
            row[f"{label}_收益"] = f"{np.mean(records)*100:.1f}%"
            row[f"{label}_样本"] = len(records)
        else:
            row[f"{label}_胜率"] = "—"
            row[f"{label}_收益"] = "—"
            row[f"{label}_样本"] = 0
    comparison_data[code] = {"name": name, "row": row, "df_merged": merged_etf}

# 打印对比表
print(f"\n{'ETF':<8} {'样本':<6} {'起始日期':<12}", end="")
for label in [t[2] for t in thresholds]:
    print(f" {label:>14}", end="")
print()
print("-" * 140)
for code, info in comparison_data.items():
    name = info["name"]
    row = info["row"]
    print(f"{code:<8} {row['成分股样本']:<6} {str(row['起始日期']):<12}", end="")
    for label in [t[2] for t in thresholds]:
        sample = row.get(f"{label}_样本", 0)
        win = row.get(f"{label}_胜率", "—")
        ret = row.get(f"{label}_收益", "—")
        if sample > 0:
            print(f" {win} {ret:>6}({sample})", end="")
        else:
            print(f" {'—':>14}", end="")
    print()

# ============================================================
# 5. 关键档位对比：5.5-6.0% 和 6.5-7.0%
# ============================================================
print("\n" + "=" * 80)
print("  关键档位深度对比 (5.5-6.0% 与 6.5-7.0%)")
print("=" * 80)
print(f"{'ETF':<8} {'名称':<14} {'起始':<12} {'5.5-6%胜率':>11} {'5.5-6%收益':>11} {'5.5-6%样本':>11} {'6.5-7%胜率':>11} {'6.5-7%收益':>11} {'6.5-7%样本':>11}")
print("-" * 110)
for code, info in comparison_data.items():
    row = info["row"]
    a = f"{row.get('5.5-6%_胜率','—'):>5} {row.get('5.5-6%_收益','—'):>8} ({row.get('5.5-6%_样本',0)})"
    b = f"{row.get('6.5-7%_胜率','—'):>5} {row.get('6.5-7%_收益','—'):>8} ({row.get('6.5-7%_样本',0)})"
    print(f"{code:<8} {info['name']:<14} {str(row['起始日期']):<12} {a:>30} {b:>30}")

# ============================================================
# 6. 综合评分 — 选出最优
# ============================================================
print("\n" + "=" * 80)
print("  综合评分 (5.5%+ 各档加权平均)")
print("=" * 80)

scores = []
for code, info in comparison_data.items():
    row = info["row"]
    df_m = info["df_merged"]

    # 计算 5.5%+ 全部样本的平均收益 (加权按样本数)
    total_records = []
    total_wins = []
    for label in ["5-5.5%", "5.5-6%", "6-6.5%", "6.5-7%", ">=7%"]:
        s = row.get(f"{label}_样本", 0)
        if s > 0:
            # 重算获取 records
            low_high = {"5-5.5%": (5, 5.5), "5.5-6%": (5.5, 6),
                        "6-6.5%": (6, 6.5), "6.5-7%": (6.5, 7),
                        ">=7%": (7, 20)}[label]
            mask = (df_m["erp"] >= low_high[0]) & (df_m["erp"] < low_high[1])
            idx = np.where(mask)[0]
            for i in idx:
                future = df_m["ret"].iloc[i+1:i+13]
                if len(future) == 12 and not future.isna().any():
                    r = (1 + future).prod() - 1
                    total_records.append(r)
                    total_wins.append(r > 0)

    if total_records:
        avg = np.mean(total_records) * 100
        win_rate = np.mean(total_wins) * 100
        # 综合评分: 平均收益 × 权重 + 胜率权重
        score = avg * 0.6 + win_rate * 0.4
        scores.append((code, info["name"], row["成分股样本"], len(total_records), avg, win_rate, score))

print(f"{'排名':<4} {'ETF':<8} {'名称':<14} {'成分股月':<8} {'触发月':<6} {'平均收益%':>10} {'胜率%':>8} {'综合分':>10}")
print("-" * 80)
scores.sort(key=lambda x: x[6], reverse=True)
for rank, (code, name, total_m, trigger_m, avg, win, sc) in enumerate(scores, 1):
    print(f"{rank:<4} {code:<8} {name:<14} {total_m:<8} {trigger_m:<6} {avg:>10.1f} {win:>8.1f} {sc:>10.1f}")

print("\n" + "=" * 80)
print(f"  🏆 综合最优: {scores[0][0]} {scores[0][1]}")
print(f"     平均收益 {scores[0][4]:.1f}% | 胜率 {scores[0][5]:.1f}%")
print("=" * 80)