# webhooks

Terraform-managed AWS app for inbound webhooks. An API Gateway **HTTP API**
fronts one Lambda per webhook. Shared handler base classes live in a Lambda
layer (`../shared/handlers`), and each webhook is a small instantiation of the
reusable `webhook_lambda` module.

This is the first service on the new Terraform/IaC foundation; the old
`lambda_crons/` and `s3_bucket_lambdas/` projects will migrate onto the same
pattern over time.

## Layout

```
webhooks/
├── main.tf                # shared HTTP API + layer + webhook module instances
├── variables.tf
├── outputs.tf
├── Makefile               # init / plan / apply / test shortcuts
├── modules/
│   └── webhook_lambda/    # reusable: zip + lambda + IAM + API route per webhook
├── functions/
│   └── github/
│       ├── app.py         # GithubWebhookHandler + lambda_handler
│       └── requirements.txt
├── events/
│   └── github-push.json   # sample HTTP API event
└── tests/
    └── smoke_test.py      # AWS-free test of handler logic

shared/handlers/python/webhook_lib/   # the Lambda layer
├── base_handler.py        # BaseHandler: lifecycle, SNS, SSM, local mode
└── webhook_handler.py     # WebhookHandler: HTTP parse/verify/dispatch/respond
```

## How a request flows

1. GitHub POSTs to `<api-base>/hooks/github`
2. API Gateway HTTP API invokes `webhook-github`
3. `WebhookHandler` parses the request, verifies the `X-Hub-Signature-256`
   HMAC (secret from SSM), parses JSON, dispatches to `_handle_webhook`
4. The handler optionally publishes an SNS notification and returns
   200 / 4xx / 5xx

## Prerequisites

```bash
brew install terraform          # not currently installed
# AWS credentials available (e.g. `aws sso login` / a configured profile)
```

Store the GitHub webhook secret in SSM (same value you paste into GitHub):

```bash
aws ssm put-parameter --name /webhooks/github/secret --type SecureString \
  --value '<your-webhook-secret>'
```

## Deploy

```bash
cd webhooks
make init
make plan               # review what will be created
make apply

# Optional: enable SNS notifications
terraform apply -var 'notify_sns_topic_arn=arn:aws:sns:us-east-1:ACCOUNT:topic'
```

State is **local** (`terraform.tfstate`, gitignored). To move to a remote S3
backend later, add a `backend "s3" {}` block in `main.tf` and run
`terraform init -migrate-state`.

After apply, copy the `github_webhook_url` output into the repo/org webhook
settings on GitHub (content type `application/json`, secret = the SSM value).

## Test locally

```bash
make test     # AWS-free smoke test (no Terraform/AWS required)
```

## Add a new webhook

1. Create `functions/<name>/app.py`:

   ```python
   from webhook_lib.webhook_handler import WebhookHandler, SignatureVerificationError

   class MyHandler(WebhookHandler):
       def verify_signature(self, raw_body, headers):
           ...  # raise SignatureVerificationError on mismatch

       def _handle_webhook(self, payload, headers):
           ...  # return a dict body (auto-wrapped in 200) or a full response

   _handler = MyHandler()

   def lambda_handler(event, context):
       return _handler.handle(event, context)
   ```

2. Add `functions/<name>/requirements.txt` (empty if no third-party deps).
3. Add a module block in `main.tf` (copy `module "github_webhook"`, change
   `name`, `source_dir`, `route_key`, and the function-specific `environment`).
4. `make apply`.

> The module zips the function dir as-is, which assumes pure-Python functions
> (deps come from the shared layer + the runtime's boto3). If a function needs
> third-party packages, add a build step that installs them before the archive.
