import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    env = ROOT / ".env"
    example = ROOT / ".env.example"
    if not env.exists() and example.exists():
        shutil.copy(example, env)
        print("Created .env from .env.example.")
        print("Run: python scripts/write_env.py")
        raise SystemExit(1)

    from app.config import AWS_S3_BUCKET

    if not AWS_S3_BUCKET:
        print("AWS_S3_BUCKET is empty.")
        print("Run: python scripts/write_env.py")
        raise SystemExit(1)

    from app.pipeline import run

    print("Loading PaySim + Plaid into S3 / Glue / Athena...")
    print(f"  S3 bucket: {AWS_S3_BUCKET}")
    try:
        result = run()
    except Exception as exc:
        print("AWS load failed.")
        print(str(exc))
        raise SystemExit(1) from exc

    print("Done.")
    for k, v in result.items():
        print(f"  {k}: {v}")
    print("\nNext:")
    print("  API:         python -m uvicorn app.api:app --port 8000")
    print("  Dashboard:   python -m streamlit run app/dashboard.py")
    print("  Athena:      http://127.0.0.1:8000/athena/gold")
    print("  Stream:      python scripts/stream_payments.py --seconds 20")


if __name__ == "__main__":
    main()
