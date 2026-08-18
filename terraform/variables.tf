variable "aws_region" {
  description = "AWS region for every resource in this demo."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short name used in resource names and tags."
  type        = string
  default     = "nfcu-cloud"
}

variable "bucket_name" {
  description = "S3 bucket name. Leave empty to auto-generate a unique name."
  type        = string
  default     = ""
}

variable "enable_kinesis" {
  description = "Create one cheap Kinesis shard (~$0.015/hour). Destroy the same day."
  type        = bool
  default     = true
}
