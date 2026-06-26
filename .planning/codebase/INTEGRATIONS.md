# External Integrations

**Analysis Date:** 2026-06-26

## APIs & External Services

**Patent Status:**
- USPTO Patent Center API — queried by `lambda_crons/patent_number/lambda_handler.py`
  - Endpoint: `https://ped.uspto.gov/api/queries` (POST)
  - Auth: None (public API)
  - Payload: loaded from `lambda_crons/patent_number/payload.json`
  - Purpose: Poll patent application status and surface recent transactions

**Traffic Court:**
- Santa Clara County Superior Court Portal — queried by `lambda_crons/traffic_ticket/lambda_handler.py`
  - Token endpoint: `http://portal.scscourt.org/api/traffic/token` (GET)
  - Search endpoint: `http://portal.scscourt.org/api/traffic/search` (POST)
  - Auth: Portal-Token header (token fetched per-request from token endpoint)
  - Secrets: `driver_license_number`, `birthdate` fetched from AWS SSM Parameter Store
  - Purpose: Check whether a traffic ticket is visible in the court system

**Home Assistant:**
- ESPHome devices expose a native API to Home Assistant — configured in all `esphome/*.yaml` files
  - API password: empty string (no authentication configured)
  - OTA updates: enabled via ESPHome OTA platform
  - Devices: `fiat_light`, `garage_door`, `garage_door_lock`, `living_room_fan`

## Data Storage

**Databases:**
- AWS DynamoDB (us-east-1, account `560983357304`)
  - `states` table — used by `lambda_crons/base/state_lambda_handler_base.py` to persist lambda run state (keyed by `id`, includes `time_updated`)
  - `salt_level` table (prod) / `salt_level_local` (dev) — stores ultrasonic sensor readings; queried by `lambda_crons/salt_level_entry_checker/lambda_handler.py`; receives DynamoDB Streams events consumed by `salt_level/lambdas/salt_level_notification/lambda_handler.py`
  - Client: boto3 `dynamodb` low-level client (not DynamoDB resource/ORM)
  - Connection: IAM role `arn:aws:iam::560983357304:role/lambda_crons_role`

**File Storage:**
- AWS S3
  - `aseaman-lambda-functions` — stores packaged Lambda `.zip` files for deployment (key format: `jobs/{function_name}_{nonce}.zip`)
  - `aseaman-public-bucket` — source bucket for MAME high score files; prefix `hi/`; triggers `s3_bucket_lambdas/mame_high_score/lambda_handler.py` on object creation
  - `aseaman-protected` — source bucket for budget CSV files; prefix `budget/`; triggers `s3_bucket_lambdas/budget_file/lambda_handler.py` on object creation
  - Client: boto3 `s3` client

**Caching:**
- None

## Authentication & Identity

**Auth Provider:**
- AWS IAM — all Lambda functions run under role `arn:aws:iam::560983357304:role/lambda_crons_role`
  - Permissions include: DynamoDB read/write, SNS publish, SSM GetParameter, S3 read/write, Lambda management, CloudWatch Events management
- AWS SSM Parameter Store — used as a secrets store for sensitive values:
  - `driver_license_number` — driver's license number for traffic ticket lookup
  - `birthdate` — date of birth for traffic ticket lookup
  - Retrieved at runtime via `get_parameter()` in `lambda_crons/base/lambda_handler_base.py` and `s3_bucket_lambdas/base/lambda_handler_base.py`
- AWS IoT — MQTT over TLS (port 8883) with certificate-based auth (ATECC508A hardware crypto chip on Arduino board); certificate stored in `arduino_secrets.h` (not committed); broker address in `arduino_secrets.h`

## Monitoring & Observability

**Notifications (SNS):**
- AWS SNS topic `arn:aws:sns:us-east-1:560983357304:lambda_crons` — receives success/error notifications from all `lambda_crons/` functions
- AWS SNS topic `arn:aws:sns:us-east-1:560983357304:SaltLevelEmail` — receives salt level threshold alerts from `salt_level/lambdas/salt_level_notification/lambda_handler.py`
- SNS message bodies are rendered from Jinja2 templates (`sns_template.jinja2`) located alongside each lambda handler
- Error notifications sent automatically by base handler on any unhandled exception

**Logs:**
- `print()` statements throughout handlers; visible in AWS CloudWatch Logs via Lambda's default log capture

**Error Tracking:**
- No dedicated error tracking service (e.g., Sentry). Errors are caught in the base `handle()` method and sent via SNS email.

## CI/CD & Deployment

**Hosting:**
- AWS Lambda (us-east-1) — all Python lambda functions
- AWS CloudWatch Events — cron schedule triggers for `lambda_crons/` functions
- AWS S3 bucket notifications — event triggers for `s3_bucket_lambdas/` functions

**Deploy Process:**
- `lambda_crons/deploy.py` — packages function + dependencies via `make`, uploads zip to S3, deletes and recreates Lambda function, configures CloudWatch Events triggers; run manually: `python deploy.py <subdir> [--profile <aws_profile>]`
- `s3_bucket_lambdas/deploy.py` — same pattern but configures S3 bucket notifications instead of CloudWatch Events

**CI Pipeline:**
- None detected. Deployment is fully manual via `deploy.py` scripts.

**ESPHome:**
- Firmware compiled via `esphome compile <config>.yaml` and flashed via OTA or serial
- Build artifacts in `esphome/.esphome/build/` (not committed)

## Environment Configuration

**Required env vars (local dev only; prod uses IAM role):**
- `ROOTDIR` — optional; base directory for deploy scripts (defaults to `os.getcwd()`)
- `<SSM_PARAM_NAME>` — any SSM parameter name can be provided as an env var when running locally without `--take-input` and without AWS access

**Secrets location:**
- AWS SSM Parameter Store (production)
- Local environment variables or interactive prompt for local dev
- `arduino_secrets.h` (not committed to git) for WiFi SSID/password, MQTT broker address, and device certificate

## Webhooks & Callbacks

**Incoming:**
- AWS S3 `ObjectCreated:Put` events → `s3_bucket_lambdas/mame_high_score/lambda_handler.py` (prefix: `hi/` in `aseaman-public-bucket`)
- AWS S3 `ObjectCreated:Put` events → `s3_bucket_lambdas/budget_file/lambda_handler.py` (prefix: `budget/` in `aseaman-protected`)
- AWS DynamoDB Streams `INSERT` events → `salt_level/lambdas/salt_level_notification/lambda_handler.py`

**Outgoing:**
- MQTT publish to `sensor/salt_level` topic on AWS IoT broker (from Arduino salt level sensor, port 8883, TLS)
- SNS publish to `lambda_crons` topic on function success/error
- SNS publish to `SaltLevelEmail` topic when sensor thresholds are crossed

---

*Integration audit: 2026-06-26*
