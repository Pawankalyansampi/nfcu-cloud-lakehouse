"""Databricks-style Spark lakehouse transforms (bronze → silver → gold).

The same logic lives in databricks/nfcu_lakehouse.py so you can run it on
Databricks Community Edition or an AWS Databricks workspace. Locally we use
pandas so you do not need Java/PySpark on Windows.
"""

from __future__ import annotations

import pandas as pd


def to_lake_types(payments: pd.DataFrame, accounts: pd.DataFrame, bank_txns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    paysim = payments.copy()
    accts = accounts.copy()
    txns = bank_txns.copy()
    txns["date"] = txns["date"].astype(str)
    return paysim, accts, txns


def gold_models(payments: pd.DataFrame, accounts: pd.DataFrame, alerts: pd.DataFrame) -> dict[str, pd.DataFrame]:
    volume = (
        payments.groupby("type", as_index=False)
        .agg(
            txn_count=("amount", "count"),
            txn_amount=("amount", "sum"),
            fraud_count=("fraud_flag", lambda s: int((s == "Yes").sum())),
        )
    )
    volume["txn_count"] = volume["txn_count"].astype("int64")
    volume["fraud_count"] = volume["fraud_count"].astype("int64")
    volume["txn_amount"] = volume["txn_amount"].astype("float64")
    fraud = (
        alerts.groupby("type", as_index=False)
        .agg(alert_count=("amount", "count"), alert_amount=("amount", "sum"))
    )
    fraud["alert_count"] = fraud["alert_count"].astype("int64")
    fraud["alert_amount"] = fraud["alert_amount"].astype("float64")
    balances = (
        accounts.groupby("account_type", as_index=False)
        .agg(account_count=("account_id", "count"), total_balance=("balance", "sum"))
    )
    balances["account_count"] = balances["account_count"].astype("int64")
    balances["total_balance"] = balances["total_balance"].astype("float64")
    return {
        "gold_daily_volume": volume,
        "gold_fraud_summary": fraud,
        "gold_account_balances": balances,
    }
