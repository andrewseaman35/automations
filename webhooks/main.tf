terraform {
  required_version = ">= 1.5"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 5.0" }
    archive = { source = "hashicorp/archive", version = "~> 2.4" }
  }
  # Local state (gitignored). To move to a remote S3 backend later, add a
  # `backend "s3" {}` block here and run `terraform init -migrate-state`.
}

provider "aws" {
  region = var.region
}

# --- Shared handlers Lambda layer -------------------------------------------
# Zips shared/handlers/ -> python/webhook_lib/... mounts at /opt/python.
data "archive_file" "shared_layer" {
  type        = "zip"
  source_dir  = "${path.root}/../shared/handlers"
  output_path = "${path.root}/.build/shared-handlers-layer.zip"
  excludes    = ["**/__pycache__/**", "**/*.pyc"]
}

resource "aws_lambda_layer_version" "shared_handlers" {
  layer_name          = "webhook-shared-handlers"
  description         = "Shared BaseHandler / WebhookHandler classes (webhook_lib)"
  filename            = data.archive_file.shared_layer.output_path
  source_code_hash    = data.archive_file.shared_layer.output_base64sha256
  compatible_runtimes = ["python3.12"]
}

# --- Shared HTTP API ---------------------------------------------------------
resource "aws_apigatewayv2_api" "webhooks" {
  name          = "webhooks"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.webhooks.id
  name        = "$default"
  auto_deploy = true
}

# --- Webhooks ----------------------------------------------------------------
module "github_webhook" {
  source = "./modules/webhook_lambda"

  name              = "github"
  source_dir        = "${path.root}/functions/github"
  route_key         = "POST /hooks/github"
  api_id            = aws_apigatewayv2_api.webhooks.id
  api_execution_arn = aws_apigatewayv2_api.webhooks.execution_arn
  layer_arns        = [aws_lambda_layer_version.shared_handlers.arn]

  secret_param  = var.github_secret_param
  sns_topic_arn = var.notify_sns_topic_arn
  environment = {
    GITHUB_WEBHOOK_SECRET_PARAM = var.github_secret_param
  }
}

# To add a new webhook, copy the module block above, change `name`,
# `source_dir`, `route_key`, and the function-specific environment.
