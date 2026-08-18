# S3 data lake (SSE-S3 so Athena and Redshift COPY work without extra KMS policy).

resource "aws_s3_bucket" "lake" {
  bucket        = local.bucket_name
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "prefixes" {
  for_each = toset([
    "lake/bronze/payments/",
    "lake/bronze/accounts/",
    "lake/bronze/bank_transactions/",
    "lake/silver/payments/",
    "lake/gold/daily_volume/",
    "lake/gold/fraud_summary/",
    "lake/gold/account_balances/",
    "warehouse/redshift/",
    "stream/landing/payments/",
    "stream/silver/payments/",
    "athena-results/",
  ])
  bucket = aws_s3_bucket.lake.id
  key    = each.value
}

resource "aws_cloudwatch_log_group" "pipeline" {
  name              = "/nfcu/cloud"
  retention_in_days = 14
}
