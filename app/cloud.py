"""Write parquet to the S3 lake and CSV for Redshift COPY. Log to CloudWatch."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO, StringIO

import pandas as pd

from app.config import AWS_CLOUDWATCH_LOG_GROUP, AWS_REGION, AWS_S3_BUCKET


LAKE_KEYS = {
    ("bronze", "payments"): "lake/bronze/payments/data.parquet",
    ("bronze", "accounts"): "lake/bronze/accounts/data.parquet",
    ("bronze", "bank_transactions"): "lake/bronze/bank_transactions/data.parquet",
    ("silver", "payments"): "lake/silver/payments/data.parquet",
    ("gold", "gold_daily_volume"): "lake/gold/daily_volume/data.parquet",
    ("gold", "gold_fraud_summary"): "lake/gold/fraud_summary/data.parquet",
    ("gold", "gold_account_balances"): "lake/gold/account_balances/data.parquet",
}


def push_to_cloud(tables: dict[str, pd.DataFrame], gold: dict[str, pd.DataFrame]) -> dict:
    if not AWS_S3_BUCKET:
        return {"status": "skipped", "reason": "AWS_S3_BUCKET is empty in .env"}

    import boto3

    s3 = boto3.client("s3", region_name=AWS_REGION)
    uploaded = []

    layers = {
        "bronze": ["payments", "accounts", "bank_transactions"],
        "silver": ["payments"],
    }
    for layer, names in layers.items():
        for name in names:
            key = LAKE_KEYS[(layer, name)]
            _put_parquet(s3, tables[name], key)
            uploaded.append(key)

    for name, df in gold.items():
        key = LAKE_KEYS[("gold", name)]
        _put_parquet(s3, df, key)
        uploaded.append(key)
        csv_key = f"warehouse/redshift/{name}.csv"
        _put_csv(s3, df, csv_key)
        uploaded.append(csv_key)

    for name in ("payments", "accounts", "fraud_alerts"):
        csv_key = f"warehouse/redshift/{name}.csv"
        _put_csv(s3, tables[name], csv_key)
        uploaded.append(csv_key)

    if AWS_CLOUDWATCH_LOG_GROUP:
        _write_log(uploaded)

    return {"status": "uploaded", "bucket": AWS_S3_BUCKET, "files": uploaded}


def _put_parquet(s3, df: pd.DataFrame, key: str) -> None:
    buf = BytesIO()
    df.to_parquet(buf, index=False)
    s3.put_object(Bucket=AWS_S3_BUCKET, Key=key, Body=buf.getvalue())


def _put_csv(s3, df: pd.DataFrame, key: str) -> None:
    buf = StringIO()
    df.to_csv(buf, index=False)
    s3.put_object(Bucket=AWS_S3_BUCKET, Key=key, Body=buf.getvalue().encode("utf-8"))


def _write_log(uploaded: list[str]) -> None:
    import boto3

    logs = boto3.client("logs", region_name=AWS_REGION)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    stream = f"run-{stamp}"
    try:
        logs.create_log_stream(logGroupName=AWS_CLOUDWATCH_LOG_GROUP, logStreamName=stream)
    except Exception:
        pass
    try:
        logs.put_log_events(
            logGroupName=AWS_CLOUDWATCH_LOG_GROUP,
            logStreamName=stream,
            logEvents=[
                {
                    "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "message": f"NFCU lakehouse load finished. Files: {', '.join(uploaded)}",
                }
            ],
        )
    except Exception:
        pass
