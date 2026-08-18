output "aws_region" {
  value = var.aws_region
}

output "s3_bucket" {
  value = aws_s3_bucket.lake.bucket
}

output "cloudwatch_log_group" {
  value = aws_cloudwatch_log_group.pipeline.name
}

output "glue_database" {
  value = aws_glue_catalog_database.lake.name
}

output "athena_workgroup" {
  value = aws_athena_workgroup.analytics.name
}

output "athena_output_s3" {
  value = "s3://${aws_s3_bucket.lake.bucket}/athena-results/"
}

output "kinesis_stream_name" {
  value = try(aws_kinesis_stream.payments[0].name, "")
}
