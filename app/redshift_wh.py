"""Migrate gold reporting tables from S3 into Amazon Redshift."""

from __future__ import annotations

from sqlalchemy import create_engine, text

from app.config import AWS_S3_BUCKET, REDSHIFT_HOST, REDSHIFT_IAM_ROLE, redshift_url

TABLES = {
    "gold_daily_volume": """
        CREATE TABLE gold_daily_volume (
            type VARCHAR(64),
            txn_count BIGINT,
            txn_amount DOUBLE PRECISION,
            fraud_count BIGINT
        )
    """,
    "gold_fraud_summary": """
        CREATE TABLE gold_fraud_summary (
            type VARCHAR(64),
            alert_count BIGINT,
            alert_amount DOUBLE PRECISION
        )
    """,
    "gold_account_balances": """
        CREATE TABLE gold_account_balances (
            account_type VARCHAR(64),
            account_count BIGINT,
            total_balance DOUBLE PRECISION
        )
    """,
}


def load_from_s3() -> dict:
    if not REDSHIFT_HOST or not REDSHIFT_IAM_ROLE or not AWS_S3_BUCKET:
        return {"status": "skipped", "reason": "Redshift env vars are empty"}

    engine = create_engine(redshift_url(), isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    loaded = []
    with engine.connect() as conn:
        for name, ddl in TABLES.items():
            conn.execute(text(f"DROP TABLE IF EXISTS {name}"))
            conn.execute(text(ddl))
            copy_sql = (
                f"COPY {name} FROM 's3://{AWS_S3_BUCKET}/warehouse/redshift/{name}.csv' "
                f"IAM_ROLE '{REDSHIFT_IAM_ROLE}' "
                "CSV IGNOREHEADER 1"
            )
            conn.execute(text(copy_sql))
            loaded.append(name)
    engine.dispose()
    return {
        "status": "loaded",
        "engine": "Amazon Redshift",
        "tables": loaded,
        "host": REDSHIFT_HOST,
    }


def query(sql: str) -> list[dict]:
    if not REDSHIFT_HOST:
        return []
    engine = create_engine(redshift_url(), pool_pre_ping=True)
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = [dict(r._mapping) for r in result]
    engine.dispose()
    return rows
