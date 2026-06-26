<!-- refreshed: 2026-06-26 -->
# Architecture

**Analysis Date:** 2026-06-26

## System Overview

This is a **monorepo of independent automation projects** — not a single unified application. Each top-level directory is a self-contained automation with its own language, runtime, and deployment model.

```text
┌──────────────────────────────────────────────────────────────────────┐
│                        Automation Projects                           │
├──────────────┬───────────────┬───────────────┬───────────────────────┤
│  lambda_crons│s3_bucket_     │  human_       │  esphome /            │
│              │lambdas        │  benchmark    │  garage_door_lock /   │
│              │               │               │  salt_level           │
│  `lambda_    │  `s3_bucket_  │  `human_      │  `esphome/*.yaml`     │
│  crons/`     │  lambdas/`    │  benchmark/`  │  `garage_door_lock/`  │
└──────┬───────┴───────┬───────┴───────┬───────┴──────────┬────────────┘
       │               │               │                  │
       ▼               ▼               ▼                  ▼
┌──────────────┐ ┌─────────────┐ ┌────────────┐  ┌──────────────────┐
│  AWS Lambda  │ │ AWS Lambda  │ │  macOS     │  │  ESP8266 /       │
│  (cron)      │ │ (S3 trigger)│ │  Desktop   │  │  Arduino         │
│  + SNS/DDB   │ │  + SNS      │ │  (CV/GUI)  │  │  Microcontroller │
└──────────────┘ └─────────────┘ └────────────┘  └──────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Key Files |
|-----------|----------------|-----------|
| `lambda_crons` | Scheduled AWS Lambda functions triggered by CloudWatch cron events | `lambda_crons/base/lambda_handler_base.py`, `lambda_crons/deploy.py` |
| `s3_bucket_lambdas` | AWS Lambda functions triggered by S3 bucket events (PutObject) | `s3_bucket_lambdas/base/lambda_handler_base.py`, `s3_bucket_lambdas/deploy.py` |
| `human_benchmark` | Computer-vision automation scripts that play browser games via screen capture and mouse control | `human_benchmark/screen.py`, `human_benchmark/util.py` |
| `esphome` | ESPHome YAML configurations for ESP8266 microcontrollers (garage door, fan, lights) | `esphome/*.yaml` |
| `expense_categorization` | CLI tool to categorize Chase credit card CSV exports | `expense_categorization/categorize.py` |
| `garage_door_lock` | Arduino sketch for a servo-based garage door lock | `garage_door_lock/garage_door_lock.ino` |
| `salt_level` | Water softener salt level sensor (Arduino) + notification Lambda | `salt_level/salt_level_sensor/salt_level_sensor.ino` |

## Pattern Overview

**Overall:** Plugin/Base-class pattern for Lambda projects; script-per-automation for desktop/embedded projects.

**Key Characteristics:**
- Both Lambda project families (`lambda_crons`, `s3_bucket_lambdas`) share an identical Template Method pattern via a `LambdaHandler` base class
- Each individual Lambda function is a subdirectory with its own `lambda_handler.py` that subclasses the base
- Desktop automations (`human_benchmark`) are standalone scripts sharing utility modules via local imports
- Embedded/firmware automations (`esphome`, `garage_door_lock`, `salt_level`) are independent and have no shared code with the Python projects

## Layers

**Lambda Base Layer:**
- Purpose: Abstract lifecycle — parse event, init AWS clients, run, send SNS notification on success/error
- Location: `lambda_crons/base/lambda_handler_base.py`, `s3_bucket_lambdas/base/lambda_handler_base.py`
- Contains: `LambdaHandler` base class with `handle()`, `_before_run()`, `_run()`, `_after_run()`, `send_sns()`, `get_parameter()`
- Depends on: `boto3`, `jinja2`
- Used by: All individual Lambda function subdirectories

**Stateful Lambda Extension (lambda_crons only):**
- Purpose: Extends base to persist run results to DynamoDB `states` table, enabling change-detection across invocations
- Location: `lambda_crons/base/state_lambda_handler_base.py`
- Contains: `StateLambdaHandler` subclass with `put_state()`, `build_state_from_result()`
- Depends on: `lambda_handler_base.py`, DynamoDB
- Used by: `lambda_crons/patent_number/lambda_handler.py`

**Individual Lambda Functions:**
- Purpose: Implement business logic in `_run(event, context)`; return a dict consumed by the Jinja2 SNS template
- Location: `lambda_crons/{function_name}/lambda_handler.py`, `s3_bucket_lambdas/{function_name}/lambda_handler.py`
- Contains: One handler class per subdirectory, a module-level `lambda_handler()` entry-point function
- Depends on: `base/` package, function-specific `requirements.txt`

**SNS Notification Templates:**
- Purpose: Render human-readable notification bodies from handler result dicts
- Location: `lambda_crons/{function_name}/sns_template.jinja2`, `s3_bucket_lambdas/{function_name}/sns_template.jinja2`
- Contains: Jinja2 templates for email/SNS message content

**Deployment & Invocation Layer:**
- Purpose: Package Lambda zip, upload to S3, create/update Lambda function and CloudWatch/S3 event triggers
- Location: `lambda_crons/deploy.py`, `s3_bucket_lambdas/deploy.py`, `lambda_crons/invoke.py`, `s3_bucket_lambdas/invoke.py`
- Contains: CLI `Deploy` and `Invoke` classes

**Human Benchmark Automation Layer:**
- Purpose: Capture a screen region, perform OpenCV color/contour analysis, fire mouse clicks via pyautogui
- Location: `human_benchmark/screen.py` (screen capture), `human_benchmark/util.py` (image analysis helpers)
- Contains: `Screen`, `BoundingBox`, `Point` dataclasses; HSV color detection utilities
- Used by: `human_benchmark/reactiontime.py`, `human_benchmark/sequence.py`, `human_benchmark/color.py`, `human_benchmark/screen_position.py`

## Data Flow

### Lambda Cron Invocation (Production)

1. CloudWatch Events fires cron trigger → AWS Lambda invokes `lambda_handler(event, context)` in `{function}/lambda_handler.py`
2. `LambdaHandler.handle()` calls `_before_run()`: parses event flags, initializes boto3 clients (DDB, SNS, SSM), loads Jinja2 template
3. `_run()` executes business logic (API calls, S3 event parsing, etc.) and returns a result dict
4. `_after_run()` renders the Jinja2 SNS template with the result dict and publishes to SNS topic `arn:aws:sns:us-east-1:560983357304:lambda_crons`
5. (For `StateLambdaHandler`) result dict is also persisted to DynamoDB table `states` with an `id` key and `time_updated` timestamp

### Lambda Local Invocation (Development)

1. Developer runs `python invoke.py {function_name} --local [--allow-aws]`
2. `invoke.py` dynamically imports `{function_name}.lambda_handler` via `importlib`
3. Injects `{'local': True, 'allow_aws': ..., ...}` event dict — same code path runs but SNS/DDB calls are suppressed unless `--allow-aws` is set

### S3-Triggered Lambda (Production)

1. S3 PutObject event on configured bucket/prefix → AWS Lambda invokes handler
2. Handler iterates `event["Records"]`, filters for `ObjectCreated:Put` events, extracts object keys
3. Returns changes list; SNS notification sent (or suppressed if `sns_arn = None` as in `budget_file`)

### Human Benchmark Automation

1. Script instantiates a task class (e.g., `ReactionTime`, `Sequence`) with a screen `BoundingBox`
2. `Screen.find_window()` shows a preview with alignment overlay; developer presses `a` to confirm alignment
3. `Screen.capture()` yields an infinite stream of numpy image arrays captured via `mss`
4. Each frame is analyzed with OpenCV HSV color range checks or contour detection
5. On match, `pyautogui.click()` fires a mouse event at the computed absolute screen coordinate

## Key Abstractions

**`LambdaHandler` (Template Method):**
- Purpose: Defines the Lambda lifecycle: setup → run → notify. Subclasses only implement `_run()`.
- Examples: `lambda_crons/base/lambda_handler_base.py`, `s3_bucket_lambdas/base/lambda_handler_base.py`
- Pattern: Template Method — `handle()` orchestrates `_before_run()`, `_run()`, `_after_run()`, `_handle_error()`

**`StateLambdaHandler` (Extension):**
- Purpose: Adds DynamoDB state persistence on top of the base lifecycle
- Examples: `lambda_crons/base/state_lambda_handler_base.py`
- Pattern: Inheritance — overrides `_after_run()` to write state before sending SNS

**`config.yml` (Per-function configuration):**
- Purpose: Declares Lambda runtime, IAM role, S3 code location, schedule/trigger configuration; consumed by `deploy.py`
- Examples: `lambda_crons/patent_number/config.yml`, `s3_bucket_lambdas/mame_high_score/config.yml`
- Pattern: Data-driven deployment — deploy script reads config; no hardcoded function metadata

**`BoundingBox` / `Screen` (Desktop automation):**
- Purpose: Encapsulates a screen region for capture and coordinate translation
- Examples: `human_benchmark/screen.py`
- Pattern: Value object (`BoundingBox`) + service object (`Screen`) with a generator-based capture loop

## Entry Points

**Lambda production entry point:**
- Location: `{project}/{function_name}/lambda_handler.py` — module-level `lambda_handler(event, context)` function
- Triggers: AWS Lambda (CloudWatch cron or S3 event)
- Responsibilities: Instantiates handler class and calls `.handle(event, context)`

**Lambda local entry point:**
- Location: `lambda_crons/invoke.py`, `s3_bucket_lambdas/invoke.py`
- Triggers: `python invoke.py {function_name} --local`
- Responsibilities: Dynamically imports handler module and invokes with synthetic local event dict

**Deployment entry point:**
- Location: `lambda_crons/deploy.py`, `s3_bucket_lambdas/deploy.py`
- Triggers: `python deploy.py {function_name} [--profile] [--region]`
- Responsibilities: Packages function zip via Makefile, uploads to S3, creates/replaces Lambda function, wires event triggers

**Desktop automation entry points:**
- Location: `human_benchmark/reactiontime.py`, `human_benchmark/sequence.py`, `human_benchmark/color.py`, `human_benchmark/screen_position.py`
- Triggers: Run directly with `python {script}.py`
- Responsibilities: Instantiate task class and call `.play()`

**ESPHome firmware entry points:**
- Location: `esphome/*.yaml`
- Triggers: `esphome compile/upload/run {yaml}` or via `esphome/Makefile`
- Responsibilities: YAML declares device config, GPIO, sensors, and automations; compiled to C++ and flashed to ESP8266

## Architectural Constraints

- **Shared base in zip package:** The `base/` directory is copied into every Lambda deployment package by the Makefile (`cp -r base $(PACKAGE_DIR)/$(LAMBDA_FUNCTION)`). Both `lambda_crons` and `s3_bucket_lambdas` maintain their own parallel copy of `lambda_handler_base.py` — they are not shared at the repo level.
- **No inter-project dependencies:** Projects in this monorepo are fully independent; no cross-directory imports exist.
- **Local vs. production mode:** The `is_local` / `allow_aws` / `take_input` flags in the event dict control AWS service suppression. All Lambda handlers must respect these flags via the base class.
- **DynamoDB state table:** `lambda_crons` stateful handlers write to a hardcoded table name `states` in us-east-1.
- **SNS ARN hardcoded:** Both base classes hardcode `arn:aws:sns:us-east-1:560983357304:lambda_crons`. S3 Lambda handlers can set `sns_arn = None` on the class to disable SNS entirely (used by `budget_file`).
- **Python packaging:** Each Lambda function must have its own `requirements.txt`; dependencies are installed into a per-function package directory by `install_venv` during build.

## Anti-Patterns

### Duplicated `lambda_handler_base.py`

**What happens:** `lambda_crons/base/lambda_handler_base.py` and `s3_bucket_lambdas/base/lambda_handler_base.py` are near-identical files maintained separately.
**Why it's wrong:** Bug fixes and improvements must be applied twice; the two files have already diverged slightly (e.g., DDB client initialization, SNS guard logic).
**Do this instead:** Extract a shared `base/` package at the repo root and reference it from both project Makefiles during packaging.

### Hardcoded AWS Account IDs and ARNs

**What happens:** SNS ARN (`arn:aws:sns:us-east-1:560983357304:lambda_crons`) and IAM role ARN are hardcoded as class attributes in `lambda_handler_base.py` and as defaults in `deploy.py`.
**Why it's wrong:** Makes it difficult to deploy to a different account or region without editing source files.
**Do this instead:** Move to `config.yml` per-function config or environment variables read at runtime.

### Screen capture credentials in ESPHome YAML

**What happens:** `esphome/garage_door.yaml` contains WiFi SSID and passwords in plaintext.
**Why it's wrong:** Secrets committed to version control are a security risk.
**Do this instead:** Use ESPHome secrets file (`secrets.yaml`) with `!secret` references.

## Error Handling

**Strategy:** Catch-all in `LambdaHandler.handle()` — any unhandled exception from `_run()` is caught, logged, and sent as an SNS error notification.

**Patterns:**
- `_handle_error(e)` formats exception message and publishes to the SNS error subject
- `traceback.print_exc()` always prints stack trace to CloudWatch logs
- Local mode: error is still raised/printed but SNS call is suppressed if `allow_aws=False`

## Cross-Cutting Concerns

**Logging:** `print()` statements throughout; no structured logging framework. CloudWatch collects Lambda stdout automatically.
**Validation:** `deploy.py` validates `config.yml` schema (required keys, format of `schedule_expressions`, presence of `{nonce}` in S3 key format).
**Authentication:** AWS access via boto3 session; local runs support `--profile` for named AWS profiles; production uses Lambda execution role.

---

*Architecture analysis: 2026-06-26*
