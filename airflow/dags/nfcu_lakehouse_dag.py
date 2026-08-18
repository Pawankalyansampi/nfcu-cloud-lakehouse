"""NFCU lakehouse DAG — local Airflow (not MWAA, to avoid extra AWS cost)."""

from __future__ import annotations

from datetime import datetime, timedelta
from urllib.request import Request, urlopen
import os

from airflow import DAG
from airflow.operators.python import PythonOperator

API = os.getenv("NFCU_API", "http://127.0.0.1:8000")


def _call(path: str, method: str = "GET") -> str:
    req = Request(f"{API}/{path.lstrip('/')}", method=method)
    with urlopen(req, timeout=180) as resp:
        body = resp.read().decode("utf-8")
        if resp.status >= 400:
            raise RuntimeError(f"{path} failed: {resp.status} {body}")
        return body


def wait_for_api() -> str:
    last = None
    for _ in range(24):
        try:
            return _call("health")
        except Exception as exc:
            last = exc
            import time

            time.sleep(5)
    raise RuntimeError(f"API not ready: {last}")


def batch_ingest() -> str:
    return _call("pipeline/run", method="POST")


def gold_models() -> str:
    return _call("gold/volume")


def data_quality() -> str:
    return _call("quality")


def athena_gold() -> str:
    return _call("athena/gold")


with DAG(
    dag_id="nfcu_banking_lakehouse",
    description="Navy Federal: batch lakehouse, Athena check, data quality",
    start_date=datetime(2025, 4, 1),
    schedule="@daily",
    catchup=False,
    default_args={"retries": 1, "retry_delay": timedelta(minutes=1)},
    tags=["nfcu", "lakehouse"],
) as dag:
    t_wait = PythonOperator(task_id="wait_for_api", python_callable=wait_for_api)
    t_batch = PythonOperator(task_id="batch_jobs", python_callable=batch_ingest)
    t_gold = PythonOperator(task_id="dbt_gold_models", python_callable=gold_models)
    t_quality = PythonOperator(task_id="data_quality", python_callable=data_quality)
    t_athena = PythonOperator(task_id="athena_gold", python_callable=athena_gold)

    t_wait >> t_batch >> t_gold >> t_quality >> t_athena
