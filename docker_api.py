"""Load the S3/Athena lakehouse, then start FastAPI (used by Docker)."""

from __future__ import annotations

from app.config import AWS_S3_BUCKET


if __name__ == "__main__":
    if not AWS_S3_BUCKET:
        raise SystemExit("AWS_S3_BUCKET is empty. Run python scripts/write_env.py on the host first.")

    from app.pipeline import run

    print("Loading PaySim + Plaid into S3 / Glue / Athena...")
    result = run()
    for key, value in result.items():
        print(f"  {key}: {value}")

    import uvicorn

    uvicorn.run("app.api:app", host="0.0.0.0", port=8000)
