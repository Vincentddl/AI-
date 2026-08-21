"""
数据库 schema — 数据血缘表
依据 data-source-spec-v1.0.md 第27节
每条 validated 数据必须记录完整血缘
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "erp.db")

SCHEMA_SQL = """
-- 通用市场数据血缘表
CREATE TABLE IF NOT EXISTS market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- 数据标识
    metric TEXT NOT NULL,              -- 指标: pe, dividend_yield, yield_10y, close
    symbol TEXT NOT NULL,              -- 证券代码: 000300 / CN10Y / 000922
    as_of_date TEXT NOT NULL,          -- 数据所属日期 (YYYY-MM-DD)
    value REAL NOT NULL,               -- 数值 (统一单位)
    unit TEXT NOT NULL,                -- 单位: percentage_points / ratio / price
    -- 血缘
    provider TEXT NOT NULL,            -- 采集程序: CSINDEX / CHINABOND
    upstream_source TEXT NOT NULL,     -- 上游源: CSINDEX_OFFICIAL / CHINABOND_OFFICIAL
    source_priority TEXT NOT NULL,     -- P0 / P1 / P2 / P3
    raw_payload_hash TEXT,             -- 原始数据哈希
    fetched_at TEXT NOT NULL,          -- 采集时间 (ISO)
    -- 校验
    validation_status TEXT NOT NULL,   -- VALIDATED / DEGRADED / UNTRUSTED / FAILED
    validator_version TEXT,            -- 校验器版本
    -- 唯一约束：同指标同代码同日期同优先级只存一条
    UNIQUE(metric, symbol, as_of_date, source_priority)
);

CREATE INDEX IF NOT EXISTS idx_market_data_lookup
    ON market_data(metric, symbol, as_of_date);

CREATE INDEX IF NOT EXISTS idx_market_data_symbol_date
    ON market_data(symbol, as_of_date);
"""


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    """初始化数据库，返回连接"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def insert_or_replace(conn: sqlite3.Connection, row: dict) -> None:
    """插入或替换一条数据（按唯一约束）"""
    sql = """
    INSERT OR REPLACE INTO market_data
        (metric, symbol, as_of_date, value, unit,
         provider, upstream_source, source_priority,
         raw_payload_hash, fetched_at, validation_status, validator_version)
    VALUES
        (:metric, :symbol, :as_of_date, :value, :unit,
         :provider, :upstream_source, :source_priority,
         :raw_payload_hash, :fetched_at, :validation_status, :validator_version)
    """
    conn.execute(sql, row)
    conn.commit()


if __name__ == "__main__":
    conn = init_db()
    # 验证表结构
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    print(f"数据库: {DB_PATH}")
    print(f"表: {tables}")
    # 验证列
    cur = conn.execute("PRAGMA table_info(market_data)")
    cols = [r[1] for r in cur.fetchall()]
    print(f"market_data 列 ({len(cols)}): {cols}")
    conn.close()
    print("✅ schema 初始化成功")
