# shared/handlers — Lambda layer

Shared handler base classes, packaged as an AWS Lambda layer and consumed by
the SAM apps in this repo (starting with `../webhooks`).

## Why the `python/` directory

A Python Lambda layer must place importable code under `python/`, because that
path is mounted at `/opt/python` and added to `sys.path`. So functions import:

```python
from webhook_lib.webhook_handler import WebhookHandler
```

## Contents

- `python/webhook_lib/base_handler.py` — `BaseHandler`: generic Lambda
  lifecycle (`_before_run` → `_run` → `_after_run`), lazy boto3 clients,
  `get_parameter` (SSM with local fallback), `notify` (SNS, topic from env),
  and a `_local` event flag for AWS-free local testing.
- `python/webhook_lib/webhook_handler.py` — `WebhookHandler`: API Gateway
  HTTP API (payload format 2.0) parsing, signature verification hook, JSON
  parsing, dispatch, and well-formed HTTP responses (including error → status
  mapping).

## Design notes (vs. the old base classes)

The old `lambda_crons` / `s3_bucket_lambdas` base classes hardcoded the SNS
ARN and AWS account ID, created clients eagerly, and were duplicated across two
projects. This layer fixes all three: config comes from the environment (set
by SAM), clients are lazy (so unit tests need no AWS), and there is one copy
shared by every SAM app via the layer.

No third-party dependencies — `boto3` is provided by the Lambda runtime, so no
build step is needed; SAM zips this directory as-is.
