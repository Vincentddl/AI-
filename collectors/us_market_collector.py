"""
美国市场 Collector (P3 源 — 东方财富 + 腾讯)
依据 data-source-spec-v1.0.md，美国模块数据源改为国内平台（无需 token）

⚠️ P3 源定位：仅用于趋势监控/外盘扫描/数据交叉验证，
   不独立触发估值类 BUY 信号（规范第2节、第14节）

数据源:
  美股指数: 腾讯 qt.gtimg.cn (实时, 无token)
    标普500 = usINX  |  纳指综合 = usIXIC  |  纳指100 = usNDX
  美国10Y国债: 东方财富 bond_zh_us_rate (无用户token)
"""
import hashlib
import datetime
import requests

TENCENT_URL = "https://qt.gtimg.cn/q=usINX,usIXIC,usNDX"
HEADERS = {"User-Agent": "Mozilla/5.0"}
VALIDATOR_VERSION = "1.0"

# 腾讯美股指数映射
US_INDICES = {
    "usINX": ("US_SP500", "S&P 500"),
    "usIXIC": ("US_NASDAQ_COMPOSITE", "Nasdaq Composite"),
    "usNDX": ("US_NASDAQ100", "Nasdaq 100"),
}

PRIORITY = "P3"  # 网页/聚合源，只能备用/监控


def fetch_us_indices() -> list[dict]:
    """腾讯实时美股三大指数"""
    r = requests.get(TENCENT_URL, headers=HEADERS, timeout=10)
    r.raise_for_status()
    text = r.content.decode("gbk", errors="ignore")

    records = []
    fetched_at = datetime.datetime.now().isoformat()

    for line in text.strip().split("\n"):
        if '="' not in line:
            continue
        tag = line.split('="')[0].replace("v_", "")
        if tag not in US_INDICES:
            continue

        parts = line.split('="')[1].split("~")
        if len(parts) < 34:
            continue

        internal_id, name = US_INDICES[tag]
        try:
            price = float(parts[3])       # 最新价
            prev_close = float(parts[4])  # 昨收
            chg_pct = float(parts[32])    # 涨跌幅% (注意是32不是33)
            date_str = parts[30].split(" ")[0]  # 日期 (注意是30不是31)
        except (ValueError, IndexError):
            continue

        raw_hash = hashlib.sha256(f"tencent:{tag}:{date_str}:{price}".encode()).hexdigest()[:16]

        records.append({
            "metric": "close",
            "symbol": internal_id,
            "as_of_date": date_str,
            "value": price,
            "unit": "price",
            "provider": "TENCENT",
            "upstream_source": "TENCENT_QT",
            "source_priority": PRIORITY,
            "raw_payload_hash": raw_hash,
            "fetched_at": fetched_at,
            "validation_status": "VALIDATED",
            "validator_version": VALIDATOR_VERSION,
        })

    return records


def fetch_us_10y() -> list[dict]:
    """东方财富 美国10年期国债收益率"""
    import akshare as ak
    import pandas as pd

    df = ak.bond_zh_us_rate()
    df["日期"] = df["日期"].astype(str)

    records = []
    fetched_at = datetime.datetime.now().isoformat()

    # 取最近 5 天
    for _, row in df.tail(5).iterrows():
        date_str = row["日期"]
        value = row.get("美国国债收益率10年")
        if pd.isna(value):
            continue

        raw_hash = hashlib.sha256(f"eastmoney:us10y:{date_str}:{value}".encode()).hexdigest()[:16]

        records.append({
            "metric": "yield_10y",
            "symbol": "US10Y",
            "as_of_date": date_str,
            "value": float(value),
            "unit": "percentage_points",
            "provider": "AKSHARE",
            "upstream_source": "EASTMONEY",
            "source_priority": PRIORITY,
            "raw_payload_hash": raw_hash,
            "fetched_at": fetched_at,
            "validation_status": "VALIDATED",
            "validator_version": VALIDATOR_VERSION,
        })

    return records


if __name__ == "__main__":
    print("=== 美国模块 Collector 测试 ===")
    indices = fetch_us_indices()
    print(f"\n美股指数: {len(indices)} 条")
    for rec in indices:
        print(f"  {rec['symbol']} = {rec['value']} (as_of {rec['as_of_date']}, {rec['source_priority']})")

    us10y = fetch_us_10y()
    print(f"\n美国10Y: {len(us10y)} 条")
    for rec in us10y[-3:]:
        print(f"  US10Y = {rec['value']}% (as_of {rec['as_of_date']}, {rec['source_priority']})")
