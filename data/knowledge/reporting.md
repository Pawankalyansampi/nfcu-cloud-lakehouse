# Reporting (demo policy)

Legacy warehouse (Amazon RDS PostgreSQL) still holds operational tables:
- payments
- accounts
- bank_transactions
- fraud_alerts

Cloud lakehouse (governed analytics):
- Amazon S3 bronze / silver / gold parquet
- AWS Glue Catalog tables
- Amazon Athena named queries in workgroup nfcu-cloud-analytics

Migrated reporting warehouses:
- Amazon Redshift gold_* tables loaded by COPY from S3
- Snowflake NFCU.GOLD (optional trial account)

The FastAPI /kpis route is the number Finance should use in the daily summary.
Athena /athena/gold and Redshift /redshift/gold are the lakehouse and warehouse checks.

This is a demo document for the RAG search. It is not an official Navy Federal policy.
