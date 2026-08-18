"""Payment events: Kinesis (1 shard) then S3 landing. Destroy the stream the same day."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="NFCU cheap Kinesis producer")
    parser.add_argument("--seconds", type=int, default=20, help="How long to send events")
    parser.add_argument("--interval", type=float, default=1.0, help="Seconds between events")
    args = parser.parse_args()

    from app.config import AWS_S3_BUCKET, KINESIS_STREAM_NAME

    if not AWS_S3_BUCKET:
        print("AWS_S3_BUCKET is empty. Run python scripts/write_env.py first.")
        raise SystemExit(1)

    from app.stream import run_stream

    if not KINESIS_STREAM_NAME:
        print("KINESIS_STREAM_NAME is empty.")
        print("In terraform.tfvars set enable_kinesis = true, then:")
        print("  terraform apply")
        print("  python scripts/write_env.py")
        raise SystemExit(1)

    print(f"Kinesis stream: {KINESIS_STREAM_NAME} (1 shard, ~$0.015/hour)")
    print(f"Consumer writes s3://{AWS_S3_BUCKET}/stream/landing/payments/")
    result = run_stream(seconds=args.seconds, interval=args.interval)
    print(result)
    print("Athena table: stream_payments")
    print("When the demo is done: terraform destroy")


if __name__ == "__main__":
    main()
