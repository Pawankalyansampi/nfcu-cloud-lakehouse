# NFCU Cloud — student lakehouse (friend architecture, cheap defaults)

Same idea as your friend’s diagram. Terraform builds AWS. **Expensive boxes stay OFF** unless you turn them on for a short demo.

Clone this repo, then work from the project root (the folder that contains `app/`, `terraform/`, and `docker-compose.yml`).

---

## Friend diagram vs this student build

| Friend box | You use | Cost if you forget it overnight |
| --- | --- | --- |
| Amazon S3 bronze | S3 `lake/bronze` | cents |
| Amazon Kinesis | **1 provisioned shard** → consumer lands JSON on S3 | ~$0.015/hour (~2¢ if you destroy in an hour; ~$11 if left a month) |
| Databricks + PySpark | Free **Databricks Community Edition** notebook `databricks/nfcu_lakehouse.py` | $0 |
| Spark Structured Streaming | `databricks/nfcu_streaming.py` reads the stream landing files | $0 on Community Edition |
| Great Expectations | `app/lakehouse.py` quality checks | $0 |
| S3 Delta silver/gold + Glue | S3 parquet + Glue Catalog | cents |
| Athena | Athena workgroup + named queries | cents per query |
| Snowflake | Optional 30-day **trial** | $0 during trial |
| dbt | `dbt/models/gold` SQL | $0 |
| Tableau | **Streamlit** dashboard | $0 |
| Airflow | Local DAG `airflow/dags/nfcu_lakehouse_dag.py` (not MWAA) | $0 |
| GitHub Actions | `.github/workflows/terraform.yml` (validate only, no apply) | $0 |
| Terraform + IAM + CloudWatch | included | near $0 |
| RDS / Redshift / VPC / KMS | **Off** (removed to control student cost) | those are the money burners |

Student default AWS bill for a 2-hour demo: **1 Kinesis shard + S3 + Athena**, usually well under $1 if you destroy the same day.

---

## How to run 

### 1. AWS CLI login

```powershell
aws configure
aws sts get-caller-identity
```

Region: `us-east-1`

### 2. Terraform (S3, Glue, Athena, Kinesis)

```powershell
cd terraform
copy terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
```

Type `yes`. This creates S3, Glue, Athena, CloudWatch, and Kinesis stream `nfcu-cloud-payments` (about a minute). Keep `enable_kinesis = true` in `terraform.tfvars`.

If `terraform` is not on PATH on Windows, use `C:\Users\nagsw\bin\terraform.exe`.

### 3. Load batch lakehouse

```powershell
cd ..
python -m pip install -r requirements.txt
python scripts/write_env.py
python run_local.py
```

### 4. API + dashboard (Tableau analog)

```powershell
python -m uvicorn app.api:app --port 8000
```

http://127.0.0.1:8000/docs  
http://127.0.0.1:8000/athena/gold  

```powershell
python -m streamlit run app/dashboard.py
```

http://127.0.0.1:8501

### 5. Real-time path (Kinesis, cheap)

```powershell
python scripts/write_env.py
python scripts/stream_payments.py --seconds 20
```

Flow: producer → **Kinesis** (1 shard) → Python consumer → S3 `stream/landing/payments/` → Athena `stream_payments`.

No Firehose and no Kinesis Analytics (those cost extra).

Then import **both** notebooks into [Databricks Community Edition](https://community.cloud.databricks.com/) (free):

- `databricks/nfcu_lakehouse.py` — batch PySpark
- `databricks/nfcu_streaming.py` — Structured Streaming

### 6. Docker (API + dashboard + Airflow)

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) and wait until it is running. Terraform must already be applied, and `.env` must exist (`python scripts/write_env.py`).

```powershell
docker compose up --build
```

First start can take several minutes (image build + S3/Athena load). Then:

| What | URL |
| --- | --- |
| API | http://127.0.0.1:8000/docs |
| Dashboard | http://127.0.0.1:8501 |
| Airflow | http://127.0.0.1:8080 (user `admin`, password `admin`) |

Optional Kinesis burst from Docker:

```powershell
docker compose --profile stream run --rm stream
```

Stop:

```powershell
docker compose down
```

You can still run without Docker using `python run_local.py` as in the steps above.

### 7. Optional Snowflake trial

[signup.snowflake.com](https://signup.snowflake.com/) → run `snowflake/setup.sql` → add `SNOWFLAKE_*` to `.env` → `python run_local.py` again.

### 8. Destroy the same day

Kinesis bills by the hour even if idle. Destroy the same day.

```powershell
cd terraform
terraform destroy
```

Type `yes`. Confirm the Kinesis stream and S3 bucket are gone.

---

## Streaming

Friend: **Kinesis → Spark Structured Streaming**.

You: **Kinesis (1 shard) → S3 landing → Glue/Athena + Databricks Structured Streaming**.

Kinesis cost to expect:

- About **$0.015 per hour** for one shard (AWS often bills a full hour)
- 20 events is essentially free on PUT charges
- Overnight ≈ 36¢; a month ≈ $11
- Do **not** use on-demand mode, Firehose, or Kinesis Analytics in this demo
