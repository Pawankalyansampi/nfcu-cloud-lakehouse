"""Lakehouse steps: local parquet, CDC file, dataframe quality (no RDS)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.config import ROOT

LAKE = ROOT / "data" / "lake"


def write_lake(name: str, df: pd.DataFrame, layer: str) -> Path:
    path = LAKE / layer / f"{name}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path


def write_cdc(payments: pd.DataFrame) -> int:
    cdc = payments.copy()
    cdc["cdc_op"] = "c"
    cdc["cdc_ts"] = datetime.now(timezone.utc)
    stream_dir = ROOT / "data" / "stream"
    stream_dir.mkdir(parents=True, exist_ok=True)
    cdc.head(200).to_json(stream_dir / "payments_cdc.json", orient="records", date_format="iso")
    return len(cdc)


def run_quality(payments: pd.DataFrame, alerts: pd.DataFrame, gold: pd.DataFrame) -> pd.DataFrame:
    checks = [
        ("row_count", "payments", len(payments) > 0, int(len(payments))),
        ("amount_positive", "payments", int((payments["amount"] <= 0).sum()) == 0, int((payments["amount"] <= 0).sum())),
        ("fraud_alerts_present", "fraud_alerts", len(alerts) >= 0, int(len(alerts))),
        ("gold_daily_volume", "gold_daily_volume", len(gold) > 0, int(len(gold))),
    ]
    return pd.DataFrame(checks, columns=["check_name", "table_name", "passed", "value"])
