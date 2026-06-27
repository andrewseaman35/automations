variable "region" {
  type    = string
  default = "us-east-1"
}

variable "github_secret_param" {
  type        = string
  default     = "/webhooks/github/secret"
  description = "SSM parameter name holding the GitHub webhook shared secret."
}

variable "notify_sns_topic_arn" {
  type        = string
  default     = ""
  description = "Optional SNS topic ARN for notifications. Empty disables SNS publishing."
}
