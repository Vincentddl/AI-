"""
中债 ChinaBond 国债收益率 Collector (P0 官方源)
依据 data-source-spec-v1.0.md 第11节

接口: https://yield.chinabond.com.cn/cbweb-pbc-web/pbc/historyQuery
参数: startDate, endDate, gjqx=0, qxId=hzsylqx(国债曲线), locale=cn_ZH
返回: HTML 表格 (曲线名称/日期/3月/6月/1年/3年/5年/7年/10年/30年)
"""
import hashlib
import datetime
import io
import pandas as pd
import requests

BASE_URL = "https://yield.chinabond.com.cn/cbweb-pbc-web/pbc/historyQuery"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://yield.chinabond.com.cn/",
}

# 单位规范：percentage_points (1.6832 表示 1.6832%)
UNIT = "percentage_points"
VALIDATOR_VERSION = "1.0"


def fetch_history(start_date: str, end_date: str) -> list[dict]:
    """
    拉取中债国债收益率曲线历史数据
    返回标准化记录列表，每条含完整血缘字段
    注意：接口查询时间段最长为 1 年
    """
    params = {
        "startDate": start_date,
        "endDate": end_date,
        "gjqx": "0",           # 0 = 全部期限
        "qxId": "hzsylqx",     # hzsylqx = 中债国债收益率曲线
        "locale": "cn_ZH",
    }
    r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()

    # 解析 HTML 表格（header=0 强制第一行为表头，因为中债用 <td> 而非 <th>）
    tables = pd.read_html(io.StringIO(r.text), header=0)
    if not tables:
        return []

    # 找到包含"日期"和"10年"列的数据表格
    df = None
    for t in tables:
        cols = [str(c) for c in t.columns]
        if any("日期" in c for c in cols) and any("10年" in c for c in cols):
            df = t
            break

    if df is None:
        return []

    # 定位列名
    date_col = [c for c in df.columns if "日期" in str(c)][0]
    y10_col = [c for c in df.columns if "10年" in str(c)][0]

    records = []
    fetched_at = datetime.datetime.now().isoformat()

    for _, row in df.iterrows():
        date_str = str(row[date_col]).strip()
        y10 = row[y10_col]
        if not date_str or date_str == "日期" or pd.isna(y10):
            continue

        # 日期格式处理 (2026-08-20)
        try:
            as_of_date = pd.to_datetime(date_str).strftime("%Y-%m-%d")
        except Exception:
            continue

        value = float(y10)
        # 校验: 0 < CN10Y < 10 (规范第11节)
        if not (0 < value < 10):
            continue

        # 原始数据哈希（用于血缘追溯）
        raw_payload_hash = hashlib.sha256(f"chinabond:{as_of_date}:{value}".encode()).hexdigest()[:16]

        records.append({
            "metric": "yield_10y",
            "symbol": "CN10Y",
            "as_of_date": as_of_date,
            "value": value,
            "unit": UNIT,
            "provider": "CHINABOND",
            "upstream_source": "CHINABOND_OFFICIAL",
            "source_priority": "P0",
            "raw_payload_hash": raw_payload_hash,
            "fetched_at": fetched_at,
            "validation_status": "VALIDATED",  # 采集后先标记，Validator 再复核
            "validator_version": VALIDATOR_VERSION,
        })

    return records


if __name__ == "__main__":
    # 测试：拉最近一周
    end = datetime.date.today()
    start = end - datetime.timedelta(days=7)
    records = fetch_history(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    print(f"拉取 {start} ~ {end}: {len(records)} 条记录")
    for rec in records[:3]:
        print(f"  {rec['as_of_date']} CN10Y = {rec['value']}% | "
              f"source={rec['upstream_source']} | status={rec['validation_status']}")
