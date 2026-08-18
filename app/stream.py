"""Kinesis → S3 landing. One cheap shard. No Firehose."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone

import numpy as np

from app.config import AWS_REGION, AWS_S3_BUCKET, KINESIS_STREAM_NAME


def make_event(rng: np.random.Generator) -> dict:
    ptype = rng.choice(["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"])
    amount = round(float(rng.lognormal(6.2, 1.2)), 2)
    fraud = ptype in {"TRANSFER", "CASH_OUT"} and amount > 8000 and rng.random() < 0.15
    return {
        "event_id": str(uuid.uuid4()),
        "event_ts": datetime.now(timezone.utc).isoformat(),
        "type": str(ptype),
        "amount": amount,
        "customer_id": f"C{100000 + int(rng.integers(0, 4000))}",
        "fraud_flag": "Yes" if fraud else "No",
    }


def _put_s3(event: dict) -> str:
    import boto3

    body = json.dumps(event)
    stamp = datetime.now(timezone.utc).strftime("%Y/%m/%d/%H")
    key = f"stream/landing/payments/{stamp}/{event['event_id']}.json"
    s3 = boto3.client("s3", region_name=AWS_REGION)
    s3.put_object(Bucket=AWS_S3_BUCKET, Key=key, Body=body.encode("utf-8"))
    return key


def put_to_kinesis(event: dict) -> None:
    import boto3

    kinesis = boto3.client("kinesis", region_name=AWS_REGION)
    kinesis.put_record(
        StreamName=KINESIS_STREAM_NAME,
        Data=json.dumps(event).encode("utf-8"),
        PartitionKey=event["customer_id"],
    )


def drain_kinesis_to_s3(limit: int = 200) -> int:
    """Read the shard and land JSON on S3 (cheap consumer, no Firehose)."""
    if not KINESIS_STREAM_NAME or not AWS_S3_BUCKET:
        return 0

    import boto3

    client = boto3.client("kinesis", region_name=AWS_REGION)
    desc = client.describe_stream(StreamName=KINESIS_STREAM_NAME)
    written = 0
    seen: set[str] = set()
    for shard in desc["StreamDescription"]["Shards"]:
        iterator = client.get_shard_iterator(
            StreamName=KINESIS_STREAM_NAME,
            ShardId=shard["ShardId"],
            ShardIteratorType="TRIM_HORIZON",
        )["ShardIterator"]
        empty = 0
        while iterator and written < limit and empty < 3:
            resp = client.get_records(ShardIterator=iterator, Limit=100)
            records = resp.get("Records") or []
            if not records:
                empty += 1
            for rec in records:
                event = json.loads(rec["Data"])
                eid = event.get("event_id")
                if eid in seen:
                    continue
                seen.add(eid)
                _put_s3(event)
                written += 1
            iterator = resp.get("NextShardIterator")
            time.sleep(0.2)
    return written


def publish_event(event: dict) -> dict:
    if not AWS_S3_BUCKET:
        return {"status": "skipped", "reason": "AWS_S3_BUCKET is empty"}

    if KINESIS_STREAM_NAME:
        put_to_kinesis(event)
        return {"status": "kinesis", "stream": KINESIS_STREAM_NAME}

    key = _put_s3(event)
    return {"status": "landed", "s3_key": key, "kinesis": "off"}


def run_stream(seconds: int = 20, interval: float = 1.0) -> dict:
    rng = np.random.default_rng()
    sent = []
    deadline = time.time() + seconds
    while time.time() < deadline:
        event = make_event(rng)
        sent.append(publish_event(event))
        time.sleep(interval)
    drained = drain_kinesis_to_s3(limit=max(len(sent) * 2, 50)) if KINESIS_STREAM_NAME else 0
    return {
        "events": len(sent),
        "kinesis": KINESIS_STREAM_NAME or "off",
        "kinesis_puts": sum(1 for r in sent if r.get("status") == "kinesis"),
        "s3_from_kinesis": drained,
        "s3_direct": sum(1 for r in sent if r.get("status") == "landed"),
    }
