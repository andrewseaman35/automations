output "function_name" {
  value = aws_lambda_function.this.function_name
}

output "function_arn" {
  value = aws_lambda_function.this.arn
}

output "route_key" {
  value = aws_apigatewayv2_route.this.route_key
}
