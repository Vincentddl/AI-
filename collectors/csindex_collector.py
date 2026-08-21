"""
中证指数估值 Collector (P0 官方源)
依据 data-source-spec-v1.0.md 第10节

接口: 中证指数官方 OSS Excel 文件
https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/indicator/{code}indicator.xls

返回字段: 日期/市盈率1(总股本)/市盈率2(计算用股本)/股息率1/股息率2
限制: 官方只提供最近 ~20 个交易日，历史必须每日落库积累
"""
import hashlib
import datetime
import pandas as pd
import requests

BASE_URL = "https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/indicator"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
VALIDATOR_VERSION = "1.0"

# 指数代码映射（中证官网格式）
INDICES = {
    "000300": "沪深300",
    "000922": "中证红利",
}


def fetch_valuation(index_code: str) -> list[dict]:
    """
    拉取指定中证指数的估值数据（PE + 股息率）
    返回标准化记录列表，含完整血缘字段
    """
    url = f"{BASE_URL}/{index_code}indicator.xls"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()

    # 用原始字节计算哈希（血缘追溯）
    raw_hash = hashlib.sha256(r.content).hexdigest()[:16]

    # 解析 Excel（用 BytesIO 从原始字节读，避免二次请求）
    import io
    df = pd.read_excel(io.BytesIO(r.content))

    fetched_at = datetime.datetime.now().isoformat()
    records = []

    for _, row in df.iterrows():
        date_val = row.get("日期Date")
        if pd.isna(date_val):
            continue

        # 日期可能是 20260730 这种 int 或 str 格式
        try:
            as_of_date = pd.to_datetime(str(date_val).split(".")[0], format="%Y%m%d").strftime("%Y-%m-%d")
        except Exception:
            try:
                as_of_date = pd.to_datetime(date_val).strftime("%Y-%m-%d")
            except Exception:
                continue

        # 采集4个指标：市盈率1/2，股息率1/2
        pe1 = row.get("市盈率1（总股本）P/E1")
        pe2 = row.get("市盈率2（计算用股本）P/E2")
        dy1 = row.get("股息率1（总股本）D/P1")
        dy2 = row.get("股息率2（计算用股本）D/P2")

        def _add(metric, value, unit):
            if pd.isna(value):
                return
            v = float(value)
            if v <= 0:
                return
            records.append({
                "metric": metric,
                "symbol": index_code,
                "as_of_date": as_of_date,
                "value": v,
                "unit": unit,
                "provider": "CSINDEX",
                "upstream_source": "CSINDEX_OFFICIAL",
                "source_priority": "P0",
                "raw_payload_hash": raw_hash,
                "fetched_at": fetched_at,
                "validation_status": "VALIDATED",
                "validator_version": VALIDATOR_VERSION,
            })

        _add("pe1_total_share", pe1, "ratio")
        _add("pe2_calc_share", pe2, "ratio")
        _add("dividend_yield1", dy1, "percentage_points")
        _add("dividend_yield2", dy2, "percentage_points")

    return records


if __name__ == "__main__":
    for code, name in INDICES.items():
        records = fetch_valuation(code)
        print(f"\n{code} {name}: {len(records)} 条记录 (含4类指标)")
        # 只展示 pe1 的最新3条
        pe1_records = [r for r in records if r["metric"] == "pe1_total_share"]
        for rec in pe1_records[-3:]:
            print(f"  {rec['as_of_date']} {name} PE(总股本) = {rec['value']} | "
                  f"source={rec['upstream_source']}")
