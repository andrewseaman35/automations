variable "name" {
  type        = string
  description = "Short webhook name, e.g. \"github\". Used for resource names."
}

variable "source_dir" {
  type        = string
  description = "Path to the function's code directory (zipped as-is)."
}

variable "route_key" {
  type        = string
  description = "HTTP API route key, e.g. \"POST /hooks/github\"."
}

variable "api_id" {
  type        = string
  description = "ID of the shared aws_apigatewayv2_api."
}

variable "api_execution_arn" {
  type        = string
  description = "execution_arn of the shared HTTP API (for the invoke permission)."
}

variable "layer_arns" {
  type        = list(string)
  default     = []
  description = "Lambda layer ARNs to attach (e.g. the shared handlers layer)."
}

variable "handler" {
  type    = string
  default = "app.lambda_handler"
}

variable "runtime" {
  type    = string
  default = "python3.12"
}

variable "architectures" {
  type    = list(string)
  default = ["arm64"]
}

variable "timeout" {
  type    = number
  default = 15
}

variable "memory_size" {
  type    = number
  default = 128
}

variable "environment" {
  type        = map(string)
  default     = {}
  description = "Extra environment variables for the function."
}

variable "secret_param" {
  type        = string
  default     = ""
  description = "SSM parameter name the function may read. Empty = no SSM access granted."
}

variable "sns_topic_arn" {
  type        = string
  default     = ""
  description = "SNS topic ARN for notifications. Empty = no SNS publish access / no topic."
}

variable "log_retention_days" {
  type    = number
  default = 14
}
