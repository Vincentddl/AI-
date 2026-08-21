import akshare as ak
import pandas as pd
import numpy as np

print("=" * 70)
print("  沪深300股债利差策略回测")
print("=" * 70)

# ========== 1. 数据获取 ==========
# 沪深300 PE + 指数点位
pe_df = ak.stock_index_pe_lg(symbol="沪深300")
pe_df["日期"] = pd.to_datetime(pe_df["日期"])
pe_df = pe_df[["日期", "指数", "滚动市盈率"]].rename(columns={"指数": "idx", "滚动市盈率": "pe_ttm"})
pe_df = pe_df.dropna(subset=["pe_ttm", "idx"])

# 10年期国债收益率
bond_df = ak.bond_zh_us_rate()
bond_df["日期"] = pd.to_datetime(bond_df["日期"])
bond_df = bond_df[["日期", "中国国债收益率10年"]].rename(columns={"中国国债收益率10年": "y10"})
bond_df = bond_df.dropna(subset=["y10"])

print(f"沪深300 PE 数据: {len(pe_df)} 条, {pe_df['日期'].min().date()} ~ {pe_df['日期'].max().date()}")
print(f"10Y国债收益率: {len(bond_df)} 条, {bond_df['日期'].min().date()} ~ {bond_df['日期'].max().date()}")

# ========== 2. 合并 + 降采样到月度 ==========
merged = pd.merge(pe_df, bond_df, on="日期", how="inner").sort_values("日期")
merged["ym"] = merged["日期"].dt.to_period("M")
monthly = merged.groupby("ym").agg({"日期": "last", "idx": "last", "pe_ttm": "last", "y10": "last"}).reset_index(drop=True)

# 计算盈利收益率和股债利差
monthly["earnings_yield"] = 100 / monthly["pe_ttm"]   # 盈利收益率 %
monthly["spread"] = monthly["earnings_yield"] - monthly["y10"]  # 股债利差 %

print(f"\n月度数据: {len(monthly)} 个月, {monthly['日期'].min().date()} ~ {monthly['日期'].max().date()}")

# ========== 3. 当前状态 ==========
last = monthly.iloc[-1]
print("\n" + "=" * 70)
print("  当前估值状态 (最新交易日)")
print("=" * 70)
print(f"  沪深300 指数: {last['idx']:.0f}")
print(f"  滚动市盈率(TTM): {last['pe_ttm']:.2f}")
print(f"  盈利收益率 = 1/PE: {last['earnings_yield']:.2f}%")
print(f"  10年期国债收益率: {last['y10']:.4f}%")
print(f"  股债利差 = 盈利收益率 - 国债: {last['spread']:.2f}%")
print(f"  策略阈值: 买入 >6% | 卖出 <4% | 当前 {last['spread']:.2f}%")

# ========== 4. 回测策略 ==========
# 信号: spread > 6 → 持有(满仓); spread < 4 → 空仓; 中间 → 维持
# 用状态机: position = 1 (持有) 或 0 (空仓)
positions = []
pos = 0
for i in range(len(monthly)):
    s = monthly["spread"].iloc[i]
    if s > 6.0:
        pos = 1
    elif s < 4.0:
        pos = 0
    # else 维持
    positions.append(pos)

monthly["position"] = positions

# 计算收益
monthly["idx_ret"] = monthly["idx"].pct_change().fillna(0)  # 指数月收益
monthly["strategy_ret"] = monthly["idx_ret"] * monthly["position"].shift(1).fillna(0)

# 净值曲线
monthly["bh_nav"] = (1 + monthly["idx_ret"]).cumprod()  # 买入持有
monthly["strategy_nav"] = (1 + monthly["strategy_ret"]).cumprod()  # 策略

# ========== 5. 统计 ==========
bh_total = monthly["bh_nav"].iloc[-1] - 1
st_total = monthly["strategy_nav"].iloc[-1] - 1

# 年化
years = len(monthly) / 12
bh_annual = (1 + bh_total) ** (1 / years) - 1
st_annual = (1 + st_total) ** (1 / years) - 1

# 最大回撤
def max_drawdown(nav):
    peak = nav.cummax()
    dd = (nav - peak) / peak
    return dd.min()

bh_dd = max_drawdown(monthly["bh_nav"])
st_dd = max_drawdown(monthly["strategy_nav"])

# 持仓时间占比
hold_ratio = monthly["position"].mean()

# 交易次数（状态切换）
switches = (monthly["position"].diff().abs() == 1).sum()

print("\n" + "=" * 70)
print("  回测结果对比")
print("=" * 70)
print(f"  回测区间: {monthly['日期'].min().date()} ~ {monthly['日期'].max().date()} ({len(monthly)}个月)")
print()
print(f"  {'指标':<14} {'买入持有':>12} {'股债利差策略':>14}")
print(f"  {'-'*44}")
print(f"  {'累计收益':<14} {bh_total*100:>11.1f}% {st_total*100:>13.1f}%")
print(f"  {'年化收益':<14} {bh_annual*100:>11.1f}% {st_annual*100:>13.1f}%")
print(f"  {'最大回撤':<14} {bh_dd*100:>11.1f}% {st_dd*100:>13.1f}%")
print(f"  {'持仓时间':<14} {'100%':>12} {hold_ratio*100:>13.1f}%")
print(f"  {'交易次数':<14} {'0':>12} {switches:>14}")

# 每年收益对比
print("\n  年度收益对比:")
monthly["year"] = monthly["日期"].dt.year
yearly = monthly.groupby("year").agg({"idx_ret": lambda x: (1+x).prod()-1, "strategy_ret": lambda x: (1+x).prod()-1})
yearly.columns = ["买入持有", "策略"]
for y, row in yearly.iterrows():
    print(f"    {y}: 买入持有 {row['买入持有']*100:+7.1f}% | 策略 {row['策略']*100:+7.1f}%")

# ========== 6. 阈值敏感性 ==========
print("\n" + "=" * 70)
print("  阈值敏感性测试 (买入阈值 / 卖出阈值)")
print("=" * 70)
print(f"  {'买入>':<6} {'卖出<':<6} {'策略累计':>10} {'最大回撤':>10} {'持仓占比':>10}")
for buy_th in [5.0, 5.5, 6.0, 6.5, 7.0]:
    for sell_th in [3.0, 3.5, 4.0, 4.5]:
        pos_lst = []
        p = 0
        for s in monthly["spread"]:
            if s > buy_th: p = 1
            elif s < sell_th: p = 0
            pos_lst.append(p)
        m = monthly.copy()
        m["p"] = pos_lst
        m["sr"] = m["idx_ret"] * m["p"].shift(1).fillna(0)
        nav = (1 + m["sr"]).cumprod()
        tot = nav.iloc[-1] - 1
        dd = max_drawdown(nav)
        hr = np.mean(pos_lst)
        print(f"  {buy_th:<6.1f} {sell_th:<6.1f} {tot*100:>9.1f}% {dd*100:>9.1f}% {hr*100:>9.1f}%")

print()
print("  利差分布:")
print(f"    历史利差: 最低 {monthly['spread'].min():.2f}% | 中位数 {monthly['spread'].median():.2f}% | 最高 {monthly['spread'].max():.2f}%")
print(f"    当前利差 {monthly['spread'].iloc[-1]:.2f}% 的历史分位: {(monthly['spread'] <= monthly['spread'].iloc[-1]).mean()*100:.1f}%")
