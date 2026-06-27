output "api_base_url" {
  description = "Base URL of the webhook HTTP API"
  value       = aws_apigatewayv2_api.webhooks.api_endpoint
}

output "github_webhook_url" {
  description = "Configure this URL in the GitHub repo/org webhook settings"
  value       = "${aws_apigatewayv2_api.webhooks.api_endpoint}/hooks/github"
}
