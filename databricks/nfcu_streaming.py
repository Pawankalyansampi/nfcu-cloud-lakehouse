# Databricks notebook source
# MAGIC %md
# MAGIC # NFCU Spark Structured Streaming
# MAGIC
# MAGIC Free Edition blocks `/FileStore`. This notebook uses a Delta table + a Unity Catalog volume.

# COMMAND ----------

import pandas as pd
from pyspark.sql.types import DoubleType, StringType, StructType

cat = spark.sql("SELECT current_catalog()").first()[0]
sch = spark.sql("SELECT current_schema()").first()[0]
spark.sql(f"CREATE VOLUME IF NOT EXISTS {cat}.{sch}.nfcu_demo")

SOURCE_TABLE = "nfcu_stream_bronze_events"
SINK = "nfcu_stream_silver_payments"
CHECKPOINT = f"/Volumes/{cat}/{sch}/nfcu_demo/checkpoint"

sample = [
    {"event_id": "e1", "event_ts": "2026-08-17T21:00:00Z", "type": "PAYMENT", "amount": 42.5, "customer_id": "C100001", "fraud_flag": "No"},
    {"event_id": "e2", "event_ts": "2026-08-17T21:00:01Z", "type": "TRANSFER", "amount": 12000.0, "customer_id": "C100002", "fraud_flag": "Yes"},
    {"event_id": "e3", "event_ts": "2026-08-17T21:00:02Z", "type": "CASH_OUT", "amount": 9500.0, "customer_id": "C100003", "fraud_flag": "Yes"},
    {"event_id": "e4", "event_ts": "2026-08-17T21:00:03Z", "type": "CASH_IN", "amount": 200.0, "customer_id": "C100004", "fraud_flag": "No"},
]
spark.createDataFrame(pd.DataFrame(sample)).write.mode("overwrite").saveAsTable(SOURCE_TABLE)
print("catalog:", cat, "schema:", sch)
print("checkpoint:", CHECKPOINT)

# COMMAND ----------

stream_df = spark.readStream.table(SOURCE_TABLE)

query = (
    stream_df.writeStream.format("delta")
    .outputMode("append")
    .option("checkpointLocation", CHECKPOINT)
    .queryName("nfcu_payments_stream")
    .trigger(availableNow=True)
    .table(SINK)
)

# COMMAND ----------

# MAGIC %md
# MAGIC Wait about 15 seconds, then run the next cell.

# COMMAND ----------

query.stop()
display(spark.table(SINK))
