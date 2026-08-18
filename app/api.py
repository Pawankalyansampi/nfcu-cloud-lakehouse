"""FastAPI over local parquet + Amazon Athena (no RDS)."""

from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse
import pandas as pd

from app.config import ROOT
from app.rag import ask

app = FastAPI(title="NFCU Cloud Lakehouse API", version="1.0.0")
LAKE = ROOT / "data" / "lake"


def _parquet(layer: str, name: str) -> pd.DataFrame:
    path = LAKE / layer / f"{name}.parquet"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def records(df: pd.DataFrame, limit: int | None = None) -> list[dict]:
    if df.empty:
        return []
    out = df.head(limit) if limit else df
    return out.to_dict(orient="records")


@app.get("/")
def home():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pipeline/run")
def pipeline_run():
    from app.pipeline import run

    return run()


@app.get("/kpis")
def kpis():
    payments = _parquet("silver", "payments")
    accounts = _parquet("bronze", "accounts")
    bank_txns = _parquet("bronze", "bank_transactions")
    alerts = payments[payments["fraud_flag"] == "Yes"] if not payments.empty else payments
    return {
        "payments": int(len(payments)),
        "accounts": int(len(accounts)),
        "bank_transactions": int(len(bank_txns)),
        "fraud_alerts": int(len(alerts)),
        "source": "local parquet lake (synced to S3)",
    }


@app.get("/payments")
def payments(limit: int = Query(50, ge=1, le=200)):
    return records(_parquet("silver", "payments"), limit=limit)


@app.get("/accounts")
def accounts():
    return records(_parquet("bronze", "accounts"))


@app.get("/fraud/alerts")
def alerts(limit: int = Query(50, ge=1, le=200)):
    df = _parquet("silver", "payments")
    if df.empty:
        return []
    return records(df[df["fraud_flag"] == "Yes"], limit=limit)


@app.get("/gold/volume")
def gold_volume():
    return records(_parquet("gold", "gold_daily_volume"))


@app.get("/gold/fraud")
def gold_fraud():
    from app.athena import run_query

    return run_query(
        "SELECT type, alert_count, alert_amount FROM gold_fraud_summary ORDER BY alert_amount DESC"
    )


@app.get("/quality")
def quality():
    from app.athena import run_query

    return run_query("SELECT type, txn_count, txn_amount, fraud_count FROM gold_daily_volume")


@app.get("/rag")
def rag(q: str = Query(..., min_length=3, description="Ask a policy question")):
    return ask(q)


@app.get("/athena/gold")
def athena_gold():
    from app.athena import run_query

    return run_query()


@app.post("/stream/run")
def stream_run(seconds: int = Query(15, ge=5, le=60)):
    from app.stream import run_stream

    return run_stream(seconds=seconds, interval=1.0)
