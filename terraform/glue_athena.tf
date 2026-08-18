# Glue Catalog + Athena = governed analytics over the S3 lake.

resource "aws_glue_catalog_database" "lake" {
  name        = replace("${var.project_name}_lake", "-", "_")
  description = "NFCU financial lakehouse catalog (bronze / silver / gold on S3)"
}

locals {
  glue_tables = {
    bronze_payments = {
      location = "lake/bronze/payments/"
      columns = [
        { name = "step", type = "bigint" },
        { name = "type", type = "string" },
        { name = "amount", type = "double" },
        { name = "customer_id", type = "string" },
        { name = "old_balance", type = "double" },
        { name = "new_balance", type = "double" },
        { name = "is_fraud", type = "bigint" },
        { name = "fraud_flag", type = "string" },
      ]
    }
    bronze_accounts = {
      location = "lake/bronze/accounts/"
      columns = [
        { name = "account_id", type = "string" },
        { name = "member_name", type = "string" },
        { name = "account_type", type = "string" },
        { name = "balance", type = "double" },
        { name = "bank", type = "string" },
        { name = "city", type = "string" },
        { name = "state", type = "string" },
      ]
    }
    bronze_bank_transactions = {
      location = "lake/bronze/bank_transactions/"
      columns = [
        { name = "transaction_id", type = "string" },
        { name = "account_id", type = "string" },
        { name = "date", type = "string" },
        { name = "description", type = "string" },
        { name = "amount", type = "double" },
      ]
    }
    silver_payments = {
      location = "lake/silver/payments/"
      columns = [
        { name = "step", type = "bigint" },
        { name = "type", type = "string" },
        { name = "amount", type = "double" },
        { name = "customer_id", type = "string" },
        { name = "old_balance", type = "double" },
        { name = "new_balance", type = "double" },
        { name = "is_fraud", type = "bigint" },
        { name = "fraud_flag", type = "string" },
      ]
    }
    gold_daily_volume = {
      location = "lake/gold/daily_volume/"
      columns = [
        { name = "type", type = "string" },
        { name = "txn_count", type = "bigint" },
        { name = "txn_amount", type = "double" },
        { name = "fraud_count", type = "bigint" },
      ]
    }
    gold_fraud_summary = {
      location = "lake/gold/fraud_summary/"
      columns = [
        { name = "type", type = "string" },
        { name = "alert_count", type = "bigint" },
        { name = "alert_amount", type = "double" },
      ]
    }
    gold_account_balances = {
      location = "lake/gold/account_balances/"
      columns = [
        { name = "account_type", type = "string" },
        { name = "account_count", type = "bigint" },
        { name = "total_balance", type = "double" },
      ]
    }
  }
}

resource "aws_glue_catalog_table" "stream_payments" {
  name          = "stream_payments"
  database_name = aws_glue_catalog_database.lake.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL       = "TRUE"
    classification = "json"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.lake.bucket}/stream/landing/payments/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      name                  = "json"
      serialization_library = "org.openx.data.jsonserde.JsonSerDe"
    }

    columns {
      name = "event_id"
      type = "string"
    }
    columns {
      name = "event_ts"
      type = "string"
    }
    columns {
      name = "type"
      type = "string"
    }
    columns {
      name = "amount"
      type = "double"
    }
    columns {
      name = "customer_id"
      type = "string"
    }
    columns {
      name = "fraud_flag"
      type = "string"
    }
  }
}

resource "aws_glue_catalog_table" "lake" {
  for_each      = local.glue_tables
  name          = each.key
  database_name = aws_glue_catalog_database.lake.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL              = "TRUE"
    classification        = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.lake.bucket}/${each.value.location}"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    dynamic "columns" {
      for_each = each.value.columns
      content {
        name = columns.value.name
        type = columns.value.type
      }
    }
  }
}

resource "aws_athena_workgroup" "analytics" {
  name          = "${var.project_name}-analytics"
  force_destroy = true

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.lake.bucket}/athena-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}

resource "aws_athena_named_query" "gold_volume" {
  name      = "nfcu_gold_daily_volume"
  workgroup = aws_athena_workgroup.analytics.name
  database  = aws_glue_catalog_database.lake.name
  query     = <<-SQL
    SELECT type, txn_count, txn_amount, fraud_count
    FROM ${aws_glue_catalog_database.lake.name}.gold_daily_volume
    ORDER BY txn_amount DESC;
  SQL
}

resource "aws_athena_named_query" "gold_fraud" {
  name      = "nfcu_gold_fraud_summary"
  workgroup = aws_athena_workgroup.analytics.name
  database  = aws_glue_catalog_database.lake.name
  query     = <<-SQL
    SELECT type, alert_count, alert_amount
    FROM ${aws_glue_catalog_database.lake.name}.gold_fraud_summary
    ORDER BY alert_amount DESC;
  SQL
}

resource "aws_athena_named_query" "silver_volume" {
  name      = "nfcu_silver_payment_volume"
  workgroup = aws_athena_workgroup.analytics.name
  database  = aws_glue_catalog_database.lake.name
  query     = <<-SQL
    SELECT type,
           COUNT(*) AS txn_count,
           SUM(amount) AS txn_amount,
           SUM(CASE WHEN fraud_flag = 'Yes' THEN 1 ELSE 0 END) AS fraud_count
    FROM ${aws_glue_catalog_database.lake.name}.silver_payments
    GROUP BY type
    ORDER BY txn_amount DESC;
  SQL
}

resource "aws_athena_named_query" "stream_payments" {
  name      = "nfcu_stream_payments"
  workgroup = aws_athena_workgroup.analytics.name
  database  = aws_glue_catalog_database.lake.name
  query     = <<-SQL
    SELECT type, COUNT(*) AS event_count, SUM(amount) AS event_amount
    FROM ${aws_glue_catalog_database.lake.name}.stream_payments
    GROUP BY type
    ORDER BY event_count DESC;
  SQL
}
