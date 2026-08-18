"""Copy Terraform outputs into .env (S3, Glue, Athena, Kinesis)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TF_DIR = ROOT / "terraform"
TF_EXE = Path(r"C:\Users\nagsw\bin\terraform.exe")


def _terraform_bin() -> str:
    if TF_EXE.exists():
        return str(TF_EXE)
    found = shutil.which("terraform")
    if found:
        return found
    print("Terraform not found. Use C:\\Users\\nagsw\\bin\\terraform.exe")
    raise SystemExit(1)


def _terraform_outputs() -> dict:
    proc = subprocess.run(
        [_terraform_bin(), "output", "-json"],
        cwd=TF_DIR,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print("Could not read Terraform outputs.")
        print("Did terraform apply finish?")
        print(proc.stderr.strip() or proc.stdout.strip())
        raise SystemExit(1)

    raw = json.loads(proc.stdout)
    return {key: item["value"] for key, item in raw.items()}


def _keep_snowflake(existing: Path) -> str:
    default = (
        "\nSNOWFLAKE_ACCOUNT=\n"
        "SNOWFLAKE_USER=\n"
        "SNOWFLAKE_PASSWORD=\n"
        "SNOWFLAKE_WAREHOUSE=NFCU_WH\n"
        "SNOWFLAKE_DATABASE=NFCU\n"
        "SNOWFLAKE_SCHEMA=GOLD\n"
    )
    if not existing.exists():
        return default
    kept = [line for line in existing.read_text(encoding="utf-8").splitlines() if line.startswith("SNOWFLAKE_")]
    return "\n" + "\n".join(kept) + "\n" if kept else default


def main() -> None:
    if not (TF_DIR / "terraform.tfstate").exists():
        print("No terraform.tfstate yet. Run terraform apply first.")
        raise SystemExit(1)

    out = _terraform_outputs()
    path = ROOT / ".env"
    snowflake = _keep_snowflake(path)
    env = f"""PAYSIM_MAX_ROWS=15000

AWS_REGION={out["aws_region"]}
AWS_S3_BUCKET={out["s3_bucket"]}
AWS_CLOUDWATCH_LOG_GROUP={out["cloudwatch_log_group"]}
GLUE_DATABASE={out["glue_database"]}
ATHENA_WORKGROUP={out["athena_workgroup"]}
KINESIS_STREAM_NAME={out.get("kinesis_stream_name") or ""}
{snowflake}"""
    path.write_text(env, encoding="utf-8")
    print(f"Wrote {path}")
    print(f"  AWS_S3_BUCKET={out['s3_bucket']}")
    print(f"  GLUE_DATABASE={out['glue_database']}")
    print(f"  ATHENA_WORKGROUP={out['athena_workgroup']}")
    print(f"  KINESIS_STREAM_NAME={out.get('kinesis_stream_name') or 'off'}")
    print("Next: python run_local.py")


if __name__ == "__main__":
    sys.exit(main())
