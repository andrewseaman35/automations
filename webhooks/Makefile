# Convenience targets for the webhooks Terraform app.
# Requires Terraform: https://developer.hashicorp.com/terraform/install
#   macOS: brew install terraform

.PHONY: init plan apply destroy fmt validate test

init:
	terraform init

plan:
	terraform plan

apply:
	terraform apply

destroy:
	terraform destroy

fmt:
	terraform fmt -recursive

validate:
	terraform validate

# Pure-Python smoke test of the handler logic (no AWS, no Terraform needed).
test:
	python3 tests/smoke_test.py
