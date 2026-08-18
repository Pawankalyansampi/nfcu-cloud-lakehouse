# Databricks notebook source
# MAGIC %md
# MAGIC # NFCU financial lakehouse (Databricks)
# MAGIC
# MAGIC Bronze → silver → gold on Spark. Import this file into Databricks
# MAGIC Community Edition or an AWS Databricks workspace:
# MAGIC Workspace → Import → `databricks/nfcu_lakehouse.py`.
# MAGIC
# MAGIC On AWS Databricks, replace the local writes with
# MAGIC `s3a://YOUR_BUCKET/lake/...` after you attach an instance profile
# MAGIC or access key that can write to the Terraform S3 bucket.

# COMMAND ----------

import numpy as np
import pandas as pd
from pyspark.sql import functions as F

# COMMAND ----------

# MAGIC %md
# MAGIC ## Bronze — Plaid-style accounts and PaySim payments

# COMMAND ----------

rng = np.random.default_rng(42)
n = 15000
types = rng.choice(
    ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"],
    size=n,
    p=[0.22, 0.35, 0.05, 0.28, 0.10],
)
amount = np.round(rng.lognormal(6.2, 1.2, n), 2)
old_org = np.round(rng.lognormal(8.0, 1.4, n), 2)
new_org = np.maximum(old_org - amount, 0).round(2)
fraud = np.zeros(n, dtype=int)
risky = np.where(np.isin(types, ["TRANSFER", "CASH_OUT"]))[0]
pick = rng.choice(risky, size=min(250, len(risky)), replace=False)
fraud[pick] = 1
amount[pick] = np.round(rng.uniform(5000, 250000, len(pick)), 2)
old_org[pick] = amount[pick]
new_org[pick] = 0

bronze_payments_pd = pd.DataFrame(
    {
        "step": rng.integers(1, 400, n),
        "type": types,
        "amount": amount,
        "customer_id": [f"C{100000 + i}" for i in rng.integers(0, 4000, n)],
        "old_balance": old_org,
        "new_balance": new_org,
        "is_fraud": fraud,
    }
)
bronze_payments = spark.createDataFrame(bronze_payments_pd)
bronze_payments.write.mode("overwrite").format("delta").saveAsTable("nfcu_bronze_payments")

# COMMAND ----------

accounts_rows = [
    {
        "account_id": f"plaid-acct-{i:03d}",
        "member_name": f"Member {i + 1}",
        "account_type": ["checking", "savings", "credit"][i % 3],
        "balance": round(float(1200 + i * 375.5), 2),
        "bank": "Plaid Sandbox Bank",
        "city": "Vienna",
        "state": "VA",
    }
    for i in range(25)
]
bronze_accounts = spark.createDataFrame(pd.DataFrame(accounts_rows))
bronze_accounts.write.mode("overwrite").format("delta").saveAsTable("nfcu_bronze_accounts")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Silver — fraud flags (governed payments)

# COMMAND ----------

silver_payments = bronze_payments.withColumn(
    "fraud_flag",
    F.when(
        (F.col("is_fraud") == 1)
        | (
            F.col("type").isin("TRANSFER", "CASH_OUT")
            & (F.col("new_balance") == 0)
            & (F.col("amount") > 8000)
        ),
        F.lit("Yes"),
    ).otherwise(F.lit("No")),
)
silver_payments.write.mode("overwrite").format("delta").saveAsTable("nfcu_silver_payments")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Gold — enterprise reporting models

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE nfcu_gold_daily_volume AS
# MAGIC SELECT
# MAGIC   type,
# MAGIC   COUNT(*) AS txn_count,
# MAGIC   SUM(amount) AS txn_amount,
# MAGIC   SUM(CASE WHEN fraud_flag = 'Yes' THEN 1 ELSE 0 END) AS fraud_count
# MAGIC FROM nfcu_silver_payments
# MAGIC GROUP BY type;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE nfcu_gold_fraud_summary AS
# MAGIC SELECT
# MAGIC   type,
# MAGIC   COUNT(*) AS alert_count,
# MAGIC   SUM(amount) AS alert_amount
# MAGIC FROM nfcu_silver_payments
# MAGIC WHERE fraud_flag = 'Yes'
# MAGIC GROUP BY type;

# COMMAND ----------

# MAGIC %sql
# MAGIC CREATE OR REPLACE TABLE nfcu_gold_account_balances AS
# MAGIC SELECT
# MAGIC   account_type,
# MAGIC   COUNT(*) AS account_count,
# MAGIC   SUM(balance) AS total_balance
# MAGIC FROM nfcu_bronze_accounts
# MAGIC GROUP BY account_type;

# COMMAND ----------

# MAGIC %sql
# MAGIC SELECT 'gold_daily_volume' AS model, COUNT(*) AS rows FROM nfcu_gold_daily_volume
# MAGIC UNION ALL
# MAGIC SELECT 'gold_fraud_summary', COUNT(*) FROM nfcu_gold_fraud_summary
# MAGIC UNION ALL
# MAGIC SELECT 'gold_account_balances', COUNT(*) FROM nfcu_gold_account_balances;
