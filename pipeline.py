"""
数据管线主流程 (Pipeline)
Collect → Validate → 入库 (SQLite)

用法: python pipeline.py [--days N]
默认拉最近 7 天
"""
import sys
import os
import datetime
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collectors import chinabond_collector, csindex_collector
from validator import validate
from db import schema


def run(days: int = 7):
    print("=" * 70)
    print("  数据管线执行 — Collect → Validate → 入库")
    print("=" * 70)

    # ========== 1. Collect ==========
    print("\n[1] 采集 ...")
    all_records = []

    # 1a. 中债 CN10Y
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    try:
        cn10y = chinabond_collector.fetch_history(
            start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        print(f"  中债 CN10Y: {len(cn10y)} 条")
        all_records.extend(cn10y)
    except Exception as e:
        print(f"  ❌ 中债采集失败: {e}")

    # 1b. 中证指数估值
    for code in ["000300", "000922"]:
        try:
            val = csindex_collector.fetch_valuation(code)
            print(f"  中证 {code}: {len(val)} 条")
            all_records.extend(val)
        except Exception as e:
            print(f"  ❌ 中证 {code} 采集失败: {e}")

    print(f"  采集总计: {len(all_records)} 条")

    # ========== 2. Validate ==========
    print("\n[2] 校验 ...")
    result = validate.validate_records(all_records)
    print(f"  通过: {len(result['passed'])} 条 | 失败: {len(result['failed'])} 条")
    for rec, reason in result["failed"][:5]:
        print(f"    ❌ {rec['metric']} {rec['as_of_date']}: {reason}")

    # 关键指标 Fail Closed 检查
    critical_ok = validate.check_critical_metrics(result["passed"])
    if not critical_ok:
        print("\n  🚨 FAIL CLOSED: 关键指标无可用数据，禁止生成交易信号")
        return None

    # ========== 3. 入库 ==========
    print("\n[3] 入库 ...")
    conn = schema.init_db()
    for rec in result["passed"]:
        schema.insert_or_replace(conn, rec)
    print(f"  入库: {len(result['passed'])} 条")

    # 统计库里现有数据
    cur = conn.execute(
        "SELECT metric, COUNT(DISTINCT as_of_date) FROM market_data GROUP BY metric")
    print("\n  库内数据概览:")
    for metric, cnt in cur.fetchall():
        print(f"    {metric}: {cnt} 个交易日")

    conn.close()

    # ========== 4. 输出最新关键指标 ==========
    print("\n[4] 最新关键指标:")
    conn2 = schema.init_db()
    for metric, symbol, name in [
        ("yield_10y", "CN10Y", "10年期国债收益率"),
        ("pe1_total_share", "000300", "沪深300 PE(总股本)"),
        ("pe1_total_share", "000922", "中证红利 PE(总股本)"),
    ]:
        cur = conn2.execute(
            "SELECT as_of_date, value, source_priority, validation_status "
            "FROM market_data WHERE metric=? AND symbol=? "
            "ORDER BY as_of_date DESC LIMIT 1",
            (metric, symbol))
        row = cur.fetchone()
        if row:
            print(f"    {name}: {row[1]} (as_of {row[0]}, {row[2]}, {row[3]})")
    conn2.close()

    print("\n✅ 管线执行完成")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    run(days=args.days)
