"""Optional Snowflake warehouse load (30-day trial account)."""

from __future__ import annotations

import pandas as pd

from app.config import (
    SNOWFLAKE_ACCOUNT,
    SNOWFLAKE_DATABASE,
    SNOWFLAKE_PASSWORD,
    SNOWFLAKE_SCHEMA,
    SNOWFLAKE_USER,
    SNOWFLAKE_WAREHOUSE,
)


def load_gold(gold: dict[str, pd.DataFrame]) -> dict:
    if not SNOWFLAKE_ACCOUNT or not SNOWFLAKE_USER or not SNOWFLAKE_PASSWORD:
        return {
            "status": "skipped",
            "reason": "Add SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD to .env",
        }

    import snowflake.connector
    from snowflake.connector.pandas_tools import write_pandas

    conn = snowflake.connector.connect(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        warehouse=SNOWFLAKE_WAREHOUSE,
        database=SNOWFLAKE_DATABASE,
        schema=SNOWFLAKE_SCHEMA,
    )
    loaded = []
    try:
        cur = conn.cursor()
        cur.execute(f"CREATE WAREHOUSE IF NOT EXISTS {SNOWFLAKE_WAREHOUSE} WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE")
        cur.execute(f"CREATE DATABASE IF NOT EXISTS {SNOWFLAKE_DATABASE}")
        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {SNOWFLAKE_DATABASE}.{SNOWFLAKE_SCHEMA}")
        cur.execute(f"USE WAREHOUSE {SNOWFLAKE_WAREHOUSE}")
        cur.execute(f"USE DATABASE {SNOWFLAKE_DATABASE}")
        cur.execute(f"USE SCHEMA {SNOWFLAKE_SCHEMA}")
        for name, df in gold.items():
            write_pandas(conn, df, name.upper(), auto_create_table=True, overwrite=True)
            loaded.append(name.upper())
        cur.close()
    finally:
        conn.close()

    return {
        "status": "loaded",
        "engine": "Snowflake",
        "database": SNOWFLAKE_DATABASE,
        "schema": SNOWFLAKE_SCHEMA,
        "tables": loaded,
    }
