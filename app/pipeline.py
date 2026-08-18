"""Load Plaid + PaySim to S3/Glue/Athena (no RDS). Optional Snowflake."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.config import PAYSIM_CSV, SAMPLE_ROWS


def make_paysim(n: int = SAMPLE_ROWS) -> pd.DataFrame:
    if PAYSIM_CSV.exists():
        return pd.read_csv(PAYSIM_CSV, nrows=n)

    rng = np.random.default_rng(42)
    types = rng.choice(
        ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"],
        size=n,
        p=[0.22, 0.35, 0.05, 0.28, 0.10],
    )
    amount = np.round(rng.lognormal(6.2, 1.2, n), 2)
    old_org = np.round(rng.lognormal(8.0, 1.4, n), 2)
    new_org = np.maximum(old_org - amount, 0).round(2)
    fraud = np.zeros(n, dtype=int)
    risky = np.where(np.isin(types, ["TRANSFER", "CASH_OUT"]))[0]
    pick = rng.choice(risky, size=min(250, len(risky)), replace=False)
    fraud[pick] = 1
    amount[pick] = np.round(rng.uniform(5000, 250000, len(pick)), 2)
    old_org[pick] = amount[pick]
    new_org[pick] = 0

    return pd.DataFrame(
        {
            "step": rng.integers(1, 400, n),
            "type": types,
            "amount": amount,
            "customer_id": [f"C{100000 + i}" for i in rng.integers(0, 4000, n)],
            "old_balance": old_org,
            "new_balance": new_org,
            "is_fraud": fraud,
        }
    )


def make_plaid_accounts() -> pd.DataFrame:
    rows = []
    for i in range(25):
        rows.append(
            {
                "account_id": f"plaid-acct-{i:03d}",
                "member_name": f"Member {i + 1}",
                "account_type": ["checking", "savings", "credit"][i % 3],
                "balance": round(float(1200 + i * 375.5), 2),
                "bank": "Plaid Sandbox Bank",
                "city": "Vienna",
                "state": "VA",
            }
        )
    return pd.DataFrame(rows)


def make_plaid_transactions(accounts: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    names = ["Payroll", "Groceries", "ATM", "Gas", "Rent", "Transfer"]
    rows = []
    today = date.today()
    acct_ids = accounts["account_id"].tolist()
    for i in range(800):
        acct = acct_ids[i % len(acct_ids)]
        rows.append(
            {
                "transaction_id": f"plaid-txn-{i:04d}",
                "account_id": acct,
                "date": today - timedelta(days=int(rng.integers(0, 60))),
                "description": names[i % len(names)],
                "amount": round(float(rng.lognormal(3.8, 0.9)), 2),
            }
        )
    return pd.DataFrame(rows)


def flag_fraud(paysim: pd.DataFrame) -> pd.DataFrame:
    df = paysim.copy()
    df["fraud_flag"] = np.where(
        (df["is_fraud"] == 1)
        | (
            (df["type"].isin(["TRANSFER", "CASH_OUT"]))
            & (df["new_balance"] == 0)
            & (df["amount"] > 8000)
        ),
        "Yes",
        "No",
    )
    return df


def run() -> dict:
    paysim = flag_fraud(make_paysim())
    accounts = make_plaid_accounts()
    bank_txns = make_plaid_transactions(accounts)
    alerts = paysim.loc[paysim["fraud_flag"] == "Yes"].copy()

    from app.lakehouse import run_quality, write_cdc, write_lake
    from app.spark_job import gold_models, to_lake_types

    write_lake("payments", paysim, "bronze")
    write_lake("accounts", accounts, "bronze")
    write_lake("bank_transactions", bank_txns, "bronze")
    write_cdc(paysim)
    write_lake("payments", paysim, "silver")

    paysim_lake, accounts_lake, txns_lake = to_lake_types(paysim, accounts, bank_txns)
    spark_gold = gold_models(paysim_lake, accounts_lake, alerts)
    write_lake("gold_daily_volume", spark_gold["gold_daily_volume"], "gold")
    dq = run_quality(paysim, alerts, spark_gold["gold_daily_volume"])

    from app.athena import run_query as run_athena
    from app.cloud import push_to_cloud
    from app.rag import build_index
    from app.snowflake_wh import load_gold as load_snowflake

    rag_docs = build_index()
    cloud = _safe(
        lambda: push_to_cloud(
            {
                "payments": paysim_lake,
                "accounts": accounts_lake,
                "bank_transactions": txns_lake,
                "fraud_alerts": alerts,
            },
            spark_gold,
        )
    )
    athena = _safe(run_athena)
    snowflake = _safe(lambda: load_snowflake(spark_gold))
    return {
        "payments": int(len(paysim)),
        "accounts": int(len(accounts)),
        "bank_transactions": int(len(bank_txns)),
        "fraud_alerts": int(len(alerts)),
        "rag_docs": rag_docs,
        "lake": "Amazon S3 + AWS Glue Catalog",
        "query": "Amazon Athena",
        "stream": "Amazon Kinesis",
        "s3": cloud.get("status"),
        "s3_files": len(cloud.get("files") or []),
        "athena": athena.get("status"),
        "athena_rows": len(athena.get("rows") or []),
        "snowflake": snowflake.get("status"),
        "quality_passed": int(dq["passed"].sum()),
        "quality_total": int(len(dq)),
    }


def _safe(fn):
    try:
        return fn()
    except Exception as exc:
        return {"status": "failed", "reason": str(exc)}
