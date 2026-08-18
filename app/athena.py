"""Amazon Athena queries over Glue Catalog tables on S3."""

from __future__ import annotations

import time

from app.config import ATHENA_WORKGROUP, AWS_REGION, GLUE_DATABASE


GOLD_VOLUME_SQL = """
SELECT type, txn_count, txn_amount, fraud_count
FROM gold_daily_volume
ORDER BY txn_amount DESC
"""


def run_query(sql: str = GOLD_VOLUME_SQL, timeout_sec: int = 90) -> dict:
    if not ATHENA_WORKGROUP or not GLUE_DATABASE:
        return {"status": "skipped", "reason": "ATHENA_WORKGROUP or GLUE_DATABASE is empty"}

    import boto3

    client = boto3.client("athena", region_name=AWS_REGION)
    started = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": GLUE_DATABASE},
        WorkGroup=ATHENA_WORKGROUP,
    )
    qid = started["QueryExecutionId"]
    deadline = time.time() + timeout_sec
    state = "RUNNING"
    while time.time() < deadline:
        info = client.get_query_execution(QueryExecutionId=qid)
        state = info["QueryExecution"]["Status"]["State"]
        if state in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            break
        time.sleep(2)

    if state != "SUCCEEDED":
        reason = info["QueryExecution"]["Status"].get("StateChangeReason", state)
        return {"status": "failed", "state": state, "reason": reason, "query_id": qid}

    result = client.get_query_results(QueryExecutionId=qid, MaxResults=50)
    rows = _parse_result(result)
    return {
        "status": "ok",
        "engine": "Amazon Athena",
        "database": GLUE_DATABASE,
        "workgroup": ATHENA_WORKGROUP,
        "query_id": qid,
        "rows": rows,
    }


def _parse_result(result: dict) -> list[dict]:
    rows = result.get("ResultSet", {}).get("Rows", [])
    if not rows:
        return []
    headers = [c.get("VarCharValue", "") for c in rows[0]["Data"]]
    out = []
    for row in rows[1:]:
        values = [c.get("VarCharValue") for c in row["Data"]]
        out.append(dict(zip(headers, values)))
    return out
