"""
数据校验程序 (Validator)
依据 data-source-spec-v1.0.md 第22/23/25节

校验链: Schema → 单位 → 日期 → 数值异常 → PASS/FAIL
关键指标失败 → Fail Closed (不凑数据)
"""
import datetime

VALIDATOR_VERSION = "1.0"

# 各 metric 的合理范围（单位统一为 percentage_points 或 ratio）
METRIC_RANGES = {
    "yield_10y":          (0.0, 10.0),    # 10年期国债收益率 %（中美通用）
    "pe1_total_share":    (3.0, 200.0),   # 市盈率1（总股本）
    "pe2_calc_share":     (3.0, 200.0),   # 市盈率2（计算用股本）
    "dividend_yield1":    (0.0, 20.0),    # 股息率1 %
    "dividend_yield2":    (0.0, 20.0),    # 股息率2 %
    "close":              (1.0, 200000.0),# 指数收盘价（美股指数可到数万点）
}

# 关键指标（失败必须 Fail Closed）
CRITICAL_METRICS = {"yield_10y", "pe1_total_share", "dividend_yield1"}

# 必填字段
REQUIRED_FIELDS = {
    "metric", "symbol", "as_of_date", "value", "unit",
    "provider", "upstream_source", "source_priority",
    "fetched_at", "validation_status",
}


def validate_record(record: dict) -> tuple[bool, str]:
    """
    校验单条记录
    返回 (是否通过, 失败原因)
    """
    # 1. Schema 验证：必填字段齐全
    missing = REQUIRED_FIELDS - set(record.keys())
    if missing:
        return False, f"schema_missing_fields:{missing}"

    # 2. 单位验证：value 是数值
    try:
        value = float(record["value"])
    except (TypeError, ValueError):
        return False, "unit_not_numeric"

    # 3. 日期验证：格式正确，且不是未来日期
    try:
        as_of = datetime.datetime.strptime(record["as_of_date"], "%Y-%m-%d")
    except ValueError:
        return False, "date_format_invalid"

    today = datetime.datetime.now().date()
    if as_of.date() > today:
        return False, "date_in_future"

    # 4. 数值异常检测：范围检查
    metric = record["metric"]
    if metric in METRIC_RANGES:
        low, high = METRIC_RANGES[metric]
        if not (low < value < high):
            return False, f"value_out_of_range:{metric}={value}"

    # 5. 来源优先级检查
    priority = record.get("source_priority", "")
    if priority not in {"P0", "P1", "P2", "P3"}:
        return False, f"invalid_priority:{priority}"

    return True, ""


def validate_records(records: list[dict]) -> dict:
    """
    校验一批记录，返回统计结果
    """
    passed = []
    failed = []
    for rec in records:
        ok, reason = validate_record(rec)
        if ok:
            rec["validation_status"] = "VALIDATED"
            rec["validator_version"] = VALIDATOR_VERSION
            passed.append(rec)
        else:
            rec["validation_status"] = "FAILED"
            rec["validator_version"] = VALIDATOR_VERSION
            failed.append((rec, reason))

    return {"passed": passed, "failed": failed}


def check_critical_metrics(records: list[dict]) -> bool:
    """
    检查关键指标是否有可用数据
    如果关键指标全部失败 → Fail Closed (返回 False，禁止生成信号)
    """
    validated_critical = {
        r["metric"] for r in records
        if r.get("validation_status") == "VALIDATED"
        and r["metric"] in CRITICAL_METRICS
    }
    return bool(validated_critical)


if __name__ == "__main__":
    # 单元测试
    test_records = [
        {
            "metric": "yield_10y", "symbol": "CN10Y", "as_of_date": "2026-08-20",
            "value": 1.6832, "unit": "percentage_points",
            "provider": "CHINABOND", "upstream_source": "CHINABOND_OFFICIAL",
            "source_priority": "P0", "fetched_at": "2026-08-21T10:00:00",
            "validation_status": "VALIDATED",
        },
        {
            "metric": "yield_10y", "symbol": "CN10Y", "as_of_date": "2026-08-20",
            "value": 15.5, "unit": "percentage_points",  # 超范围
            "provider": "CHINABOND", "upstream_source": "CHINABOND_OFFICIAL",
            "source_priority": "P0", "fetched_at": "2026-08-21T10:00:00",
            "validation_status": "VALIDATED",
        },
        {
            "metric": "yield_10y", "symbol": "CN10Y", "as_of_date": "2026-08-20",
            "value": 1.68,  # 缺字段 source_priority
            "unit": "percentage_points",
            "provider": "CHINABOND", "upstream_source": "CHINABOND_OFFICIAL",
            "fetched_at": "2026-08-21T10:00:00",
            "validation_status": "VALIDATED",
        },
    ]

    result = validate_records(test_records)
    print(f"通过: {len(result['passed'])} 条")
    print(f"失败: {len(result['failed'])} 条")
    for rec, reason in result["failed"]:
        print(f"  ❌ {rec['metric']} {rec['as_of_date']}: {reason}")
    print(f"关键指标可用: {check_critical_metrics(result['passed'])}")
