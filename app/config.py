import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost").strip()
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432").strip()
POSTGRES_USER = os.getenv("POSTGRES_USER", "nfcu_admin").strip()
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres").strip()
POSTGRES_DB = os.getenv("POSTGRES_DB", "nfcu_simple").strip()
POSTGRES_SSLMODE = os.getenv("POSTGRES_SSLMODE", "prefer").strip()

PAYSIM_CSV = ROOT / "data" / "raw" / "PS_20174392719_1491204439457_log.csv"
SAMPLE_ROWS = int(os.getenv("PAYSIM_MAX_ROWS", "15000"))
KNOWLEDGE_DIR = ROOT / "data" / "knowledge"

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET", "").strip()
AWS_CLOUDWATCH_LOG_GROUP = os.getenv("AWS_CLOUDWATCH_LOG_GROUP", "").strip()
GLUE_DATABASE = os.getenv("GLUE_DATABASE", "").strip()
ATHENA_WORKGROUP = os.getenv("ATHENA_WORKGROUP", "").strip()
KINESIS_STREAM_NAME = os.getenv("KINESIS_STREAM_NAME", "").strip()

REDSHIFT_HOST = os.getenv("REDSHIFT_HOST", "").strip()
REDSHIFT_PORT = os.getenv("REDSHIFT_PORT", "5439").strip()
REDSHIFT_USER = os.getenv("REDSHIFT_USER", "nfcu_admin").strip()
REDSHIFT_PASSWORD = os.getenv("REDSHIFT_PASSWORD", "").strip()
REDSHIFT_DB = os.getenv("REDSHIFT_DB", "nfcu").strip()
REDSHIFT_IAM_ROLE = os.getenv("REDSHIFT_IAM_ROLE", "").strip()

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "").strip()
SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER", "").strip()
SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD", "").strip()
SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "NFCU_WH").strip()
SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "NFCU").strip()
SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "GOLD").strip()


def database_url(db: str | None = None) -> str:
    name = db or POSTGRES_DB
    user = quote_plus(POSTGRES_USER)
    password = quote_plus(POSTGRES_PASSWORD)
    url = (
        f"postgresql+psycopg2://{user}:{password}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{name}"
    )
    if POSTGRES_SSLMODE:
        url += f"?sslmode={POSTGRES_SSLMODE}"
    return url


def redshift_url() -> str:
    user = quote_plus(REDSHIFT_USER)
    password = quote_plus(REDSHIFT_PASSWORD)
    return (
        f"postgresql+psycopg2://{user}:{password}"
        f"@{REDSHIFT_HOST}:{REDSHIFT_PORT}/{REDSHIFT_DB}?sslmode=require"
    )
