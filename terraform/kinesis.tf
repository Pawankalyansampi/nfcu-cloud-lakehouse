# 1 provisioned shard, 24h retention. No Firehose, Analytics, or extra shard metrics.
# About $0.015 per shard-hour. Destroy the same day.

resource "aws_kinesis_stream" "payments" {
  count                     = var.enable_kinesis ? 1 : 0
  name                      = "${var.project_name}-payments"
  shard_count               = 1
  retention_period          = 24
  enforce_consumer_deletion = true

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = { Name = "${var.project_name}-payments-stream" }
}
