"""
ERP 策略引擎 — 读库算 ERP，输出 BUY/WAIT
依据 data-source-spec-v1.0.md + erp-strategy-executable.md

公式: erp = 100 / PE_静态_总股本 - CN10Y
口径: 中证官方市盈率1(总股本) + 中债官方10年期国债收益率
关键: latest common date（PE 和国债取共同最新日期，不混用）
"""
import sys
import os
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.schema import DB_PATH

# 5 档阈值（已定死，multiple = B 的倍数）
# 依据 erp-strategy-executable.md:
#   <5.0→0 | 5.0-5.5→0.5(需二级过滤) | 5.5-6.0→0.5 | 6.0-6.5→1.0 | 6.5-7.0→1.5 | >=7.0→2.0
THRESHOLDS = [
    (5.0, "WAIT 不买", 0.0),
    (5.5, "观察区 试探", 0.5),
    (6.0, "轻度定投", 0.5),
    (6.5, "正常定投", 1.0),
    (7.0, "强定投", 1.5),
    (float("inf"), "极强定投", 2.0),
]

B_STANDARD = 3000  # 标准单次购买金额


def get_latest_common_date(conn, pe_symbol, yield_symbol):
    """
    找 PE 和国债都有数据的最新共同日期（规范第24节）
    """
    cur = conn.execute("""
        SELECT a.as_of_date
        FROM (SELECT DISTINCT as_of_date FROM market_data
              WHERE metric='pe1_total_share' AND symbol=? AND validation_status='VALIDATED') a
        INNER JOIN (SELECT DISTINCT as_of_date FROM market_data
                    WHERE metric='yield_10y' AND symbol=? AND validation_status='VALIDATED') b
        ON a.as_of_date = b.as_of_date
        ORDER BY a.as_of_date DESC LIMIT 1
    """, (pe_symbol, yield_symbol))
    row = cur.fetchone()
    return row[0] if row else None


def get_value(conn, metric, symbol, as_of_date):
    cur = conn.execute(
        "SELECT value, source_priority, validation_status FROM market_data "
        "WHERE metric=? AND symbol=? AND as_of_date=? "
        "ORDER BY CASE source_priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END "
        "LIMIT 1",
        (metric, symbol, as_of_date))
    return cur.fetchone()


def compute_erp(conn, pe_symbol="000300", yield_symbol="CN10Y"):
    """读库算 ERP，返回完整决策结果"""
    common_date = get_latest_common_date(conn, pe_symbol, yield_symbol)
    if not common_date:
        return {"status": "NO_DATA", "message": "PE 和国债无共同日期，无法计算 ERP"}

    pe_row = get_value(conn, "pe1_total_share", pe_symbol, common_date)
    yield_row = get_value(conn, "yield_10y", yield_symbol, common_date)

    if not pe_row or not yield_row:
        return {"status": "NO_DATA", "message": "数据缺失"}

    pe = pe_row[0]
    y10 = yield_row[0]
    erp = 100.0 / pe - y10

    # 档位判断
    for threshold, label, multiple in THRESHOLDS:
        if erp < threshold:
            decision = label
            b_amount = B_STANDARD * multiple
            break

    return {
        "status": "OK",
        "as_of_date": common_date,
        "pe": pe,
        "pe_source": pe_row[1],
        "yield_10y": y10,
        "yield_source": yield_row[1],
        "erp": round(erp, 4),
        "decision": decision,
        "b_multiple": multiple,
        "b_amount": b_amount,
    }


def run():
    conn = sqlite3.connect(DB_PATH)
    result = compute_erp(conn)
    conn.close()

    print("=" * 70)
    print("  ERP 策略引擎 — 决策输出")
    print("=" * 70)

    if result["status"] == "NO_DATA":
        print(f"  🚨 {result['message']}")
        print("  (Fail Closed: 不生成交易信号)")
        return

    print(f"  数据日期: {result['as_of_date']} (latest common date)")
    print(f"  沪深300 PE(总股本): {result['pe']} (源: {result['pe_source']})")
    print(f"  10年期国债: {result['yield_10y']}% (源: {result['yield_source']})")
    print(f"  ──────────────────────────────")
    print(f"  ERP = 100/{result['pe']} - {result['yield_10y']} = {result['erp']}%")
    print(f"  ──────────────────────────────")
    print(f"  📌 决策: {result['decision']}")
    print(f"  建议买入: {result['b_amount']} 元 (B={B_STANDARD} × {result['b_multiple']})")

    return result


if __name__ == "__main__":
    run()
