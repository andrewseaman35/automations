# Codebase Structure

**Analysis Date:** 2026-06-26

## Directory Layout

```
automations/                          # Monorepo root
├── esphome/                          # ESPHome firmware configs for ESP8266 devices
│   ├── fiat_lights.yaml              # Fiat exterior lights control
│   ├── garage_door.yaml              # Garage door sensor + toggle button
│   ├── garage_door_lock.yaml         # Garage door lock device config
│   ├── gdtest.yaml                   # Garage door test/development config
│   ├── living_room_fan.yaml          # Living room fan controller
│   ├── Makefile                      # esphome compile/upload/logs/run targets
│   └── .esphome/                     # Generated build artifacts (not committed)
│
├── expense_categorization/           # Chase credit card CSV categorization tool
│   ├── categorize.py                 # Main CLI script; Config class + categorization logic
│   ├── config.json                   # Category keyword mapping (shared template)
│   ├── andrew.json                   # Personal category config (gitignored pattern)
│   ├── inputs/                       # Input CSV files from Chase (gitignored)
│   ├── output/                       # Generated output reports (gitignored)
│   └── done/                         # Processed input archives
│
├── garage_door_lock/                 # Arduino servo lock sketch
│   └── garage_door_lock.ino          # Servo-based lock/unlock loop
│
├── human_benchmark/                  # Computer-vision automation for humanbenchmark.com
│   ├── screen.py                     # Screen capture: Screen, BoundingBox dataclasses
│   ├── util.py                       # Image analysis: Point, HSV color detection, contour utils
│   ├── reactiontime.py               # Reaction time game automation script
│   ├── sequence.py                   # Sequence memory game automation script
│   ├── color.py                      # Color matching game automation script
│   ├── screen_position.py            # Screen position helper/calibration script
│   ├── test_find.py                  # Standalone prototype/sandbox (duplicates some classes)
│   ├── __init__.py                   # Package marker
│   └── venv/                         # Local virtual environment (not committed)
│
├── lambda_crons/                     # AWS Lambda functions triggered by CloudWatch cron
│   ├── base/                         # Shared base classes for all cron lambdas
│   │   ├── lambda_handler_base.py    # LambdaHandler base class (Template Method)
│   │   ├── state_lambda_handler_base.py  # StateLambdaHandler — adds DynamoDB state persistence
│   │   ├── requirements.txt          # Base dependencies: boto3, jinja2
│   │   └── __init__.py
│   ├── patent_number/                # Polls USPTO API for patent application status
│   │   ├── lambda_handler.py         # PatentNumberLambdaHandler (extends StateLambdaHandler)
│   │   ├── config.yml                # Runtime, schedule, S3 package location
│   │   ├── payload.json              # USPTO API request body
│   │   ├── sns_template.jinja2       # SNS notification body template
│   │   └── requirements.txt
│   ├── salt_level_entry_checker/     # Checks water softener salt level entries
│   │   ├── lambda_handler.py
│   │   ├── config.yml
│   │   ├── sns_template.jinja2
│   │   └── requirements.txt
│   ├── traffic_ticket/               # Traffic ticket status checker
│   │   ├── lambda_handler.py
│   │   ├── config.yml
│   │   ├── sns_template.jinja2
│   │   └── requirements.txt
│   ├── packages/                     # Build output (zip packages) — generated, not committed
│   ├── install_venv/                 # Virtualenv for packaging dependencies
│   ├── deploy_venv/                  # Virtualenv for running deploy.py
│   ├── deploy.py                     # CLI: package + upload + create/update Lambda + set triggers
│   ├── invoke.py                     # CLI: invoke Lambda locally or via AWS SDK
│   ├── Makefile                      # package, clean targets used by deploy.py
│   └── requirements.txt              # deploy.py dependencies: boto3, pyyaml
│
├── s3_bucket_lambdas/                # AWS Lambda functions triggered by S3 PutObject events
│   ├── base/                         # Shared base class (parallel to lambda_crons/base)
│   │   ├── lambda_handler_base.py    # LambdaHandler base class (slightly newer version)
│   │   ├── requirements.txt
│   │   └── __init__.py
│   ├── mame_high_score/              # Notifies on new MAME arcade high score files
│   │   ├── lambda_handler.py         # MAMEHighScoreLambdaHandler
│   │   ├── config.yml                # S3 trigger bucket/prefix, runtime, package location
│   │   ├── sns_template.jinja2
│   │   └── requirements.txt
│   ├── budget_file/                  # Logs budget file uploads (SNS disabled)
│   │   ├── lambda_handler.py         # BudgetFileLambdaHandler (sns_arn = None)
│   │   ├── config.yml
│   │   └── requirements.txt
│   ├── packages/                     # Build output — generated, not committed
│   ├── install_venv/                 # Virtualenv for packaging
│   ├── deploy_venv/                  # Virtualenv for deploy.py
│   ├── deploy.py                     # CLI: same pattern as lambda_crons/deploy.py
│   ├── invoke.py                     # CLI: local/remote invocation
│   ├── Makefile                      # package, clean targets
│   ├── requirements.txt              # deploy.py dependencies
│   └── test_events/                  # Sample S3 event JSON payloads for local testing
│       └── put-budget.json
│
├── s3_backup/                        # S3 backup scripts (empty — placeholder)
│
├── salt_level/                       # Water softener salt level sensor system
│   ├── salt_level_sensor/
│   │   └── salt_level_sensor.ino     # Arduino sketch (reads sensor, publishes to AWS IoT)
│   └── lambdas/
│       └── salt_level_notification/  # Lambda to notify on low salt readings
│
├── .planning/                        # GSD planning documents
│   └── codebase/                     # Auto-generated codebase analysis docs
│
├── .gitignore                        # Root gitignore
└── README.md                         # Minimal project readme
```

## Directory Purposes

**`esphome/`:**
- Purpose: ESPHome YAML device configurations for home automation hardware
- Contains: One `.yaml` file per physical device; `Makefile` for compile/flash/logs workflow
- Key files: `esphome/garage_door.yaml`, `esphome/living_room_fan.yaml`, `esphome/fiat_lights.yaml`

**`lambda_crons/base/` and `s3_bucket_lambdas/base/`:**
- Purpose: Base handler classes shared across all Lambda functions within each project
- Contains: `LambdaHandler`, `StateLambdaHandler` — the core lifecycle framework
- Key files: `lambda_crons/base/lambda_handler_base.py`, `lambda_crons/base/state_lambda_handler_base.py`

**`{lambda_project}/{function_name}/`:**
- Purpose: One self-contained Lambda function — business logic, notification template, config, and requirements
- Contains: `lambda_handler.py`, `config.yml`, `sns_template.jinja2`, `requirements.txt`
- Pattern: Each function subdirectory is independently deployable

**`human_benchmark/`:**
- Purpose: Screen-capture automation scripts using OpenCV + pyautogui
- Contains: Shared infrastructure (`screen.py`, `util.py`) plus one script per game task
- Key files: `human_benchmark/screen.py`, `human_benchmark/util.py`

**`expense_categorization/`:**
- Purpose: CLI tool to process Chase bank CSV exports into categorized spending reports
- Contains: Single `categorize.py` script, JSON config with keyword-to-category mappings, input/output directories

## Key File Locations

**Entry Points:**
- `lambda_crons/{function}/lambda_handler.py`: Lambda production entry — `lambda_handler(event, context)` function
- `lambda_crons/invoke.py`: Local Lambda invocation CLI
- `lambda_crons/deploy.py`: Lambda deployment CLI
- `s3_bucket_lambdas/{function}/lambda_handler.py`: S3-triggered Lambda production entry
- `s3_bucket_lambdas/invoke.py`: Local S3 Lambda invocation CLI
- `s3_bucket_lambdas/deploy.py`: S3 Lambda deployment CLI
- `human_benchmark/reactiontime.py`: Run directly — `python reactiontime.py`
- `human_benchmark/sequence.py`: Run directly — `python sequence.py`
- `expense_categorization/categorize.py`: Run directly — `python categorize.py`

**Configuration:**
- `lambda_crons/{function}/config.yml`: Per-function Lambda deployment config (runtime, schedule, S3 key)
- `s3_bucket_lambdas/{function}/config.yml`: Per-function Lambda deployment config (runtime, S3 trigger bucket/prefix)
- `expense_categorization/config.json`: Category keyword mapping for expense categorization
- `esphome/*.yaml`: Device firmware configuration

**Core Logic:**
- `lambda_crons/base/lambda_handler_base.py`: Lambda lifecycle base class
- `lambda_crons/base/state_lambda_handler_base.py`: Stateful Lambda extension (DynamoDB persistence)
- `s3_bucket_lambdas/base/lambda_handler_base.py`: S3 Lambda lifecycle base class
- `human_benchmark/screen.py`: Screen capture + bounding box utilities
- `human_benchmark/util.py`: OpenCV image analysis helpers

**Notification Templates:**
- `lambda_crons/{function}/sns_template.jinja2`: Jinja2 template for SNS notification body
- `s3_bucket_lambdas/{function}/sns_template.jinja2`: Jinja2 template for SNS notification body

**Testing:**
- `s3_bucket_lambdas/test_events/put-budget.json`: Sample S3 event payload for local invoke testing
- `lambda_crons/{function}/payload.json`: Sample API payloads for local testing (where applicable)

## Naming Conventions

**Files:**
- Lambda handler files: `lambda_handler.py` (consistent across all functions)
- Base class files: `lambda_handler_base.py`, `state_lambda_handler_base.py`
- Deployment config: `config.yml` (every Lambda function subdirectory)
- Notification templates: `sns_template.jinja2` (every Lambda function subdirectory that uses SNS)
- Arduino sketches: `{project_name}.ino` (matches parent directory name)
- ESPHome configs: `{device_name}.yaml` (snake_case device names)
- Python scripts: `snake_case.py`

**Directories:**
- Lambda function subdirectories: `snake_case` (e.g., `patent_number`, `mame_high_score`, `budget_file`)
- Project directories: `snake_case` (e.g., `lambda_crons`, `s3_bucket_lambdas`, `human_benchmark`)

**Classes:**
- Lambda handlers: `{FunctionName}LambdaHandler` (e.g., `MAMEHighScoreLambdaHandler`, `PatentNumberLambdaHandler`)
- Base classes: `LambdaHandler`, `StateLambdaHandler`
- Data classes: `PascalCase` (e.g., `BoundingBox`, `Point`, `Screen`, `Config`)

**Functions:**
- Lambda entry points: always named `lambda_handler(event, context)` at module level
- Private methods: `_snake_case` prefix (e.g., `_run`, `_before_run`, `_parse_event`)
- Public methods: `snake_case` (e.g., `handle`, `send_sns`, `get_parameter`)

## Where to Add New Code

**New cron-triggered Lambda function:**
1. Create `lambda_crons/{function_name}/` directory
2. Add `lambda_handler.py` — subclass `LambdaHandler` or `StateLambdaHandler` from `base/`
3. Add `config.yml` — define `runtime`, `schedule_expressions`, `code.s3_bucket`, `code.s3_key_format`
4. Add `sns_template.jinja2` — Jinja2 template for notification content
5. Add `requirements.txt` — function-specific pip dependencies
6. Deploy with: `python deploy.py {function_name} --profile {profile}`

**New S3-triggered Lambda function:**
1. Create `s3_bucket_lambdas/{function_name}/` directory
2. Add `lambda_handler.py` — subclass `LambdaHandler` from `s3_bucket_lambdas/base/`
3. Add `config.yml` — define `runtime`, `event_type: s3`, `trigger_bucket`, `trigger_prefix`, `code.*`
4. Add `sns_template.jinja2` (or set `sns_arn = None` on the class to skip SNS)
5. Add `requirements.txt`
6. Deploy with: `python deploy.py {function_name} --profile {profile}`

**New ESPHome device:**
1. Add `esphome/{device_name}.yaml` — follow existing YAML structure for board, wifi, components
2. Use `make YAML={device_name}.yaml compile` to test; `make YAML={device_name}.yaml upload` to flash

**New human_benchmark automation:**
1. Add `human_benchmark/{game_name}.py`
2. Import `Screen`, `BoundingBox` from `human_benchmark/screen.py`
3. Import color/contour utilities from `human_benchmark/util.py`
4. Create a task class with a `play()` method; invoke at module bottom with `if __name__ == "__main__":`

**Utilities:**
- Lambda shared utilities: Add to `lambda_crons/base/` or `s3_bucket_lambdas/base/` and include in the base package
- Desktop automation shared utilities: Add to `human_benchmark/util.py`

## Special Directories

**`lambda_crons/packages/` and `s3_bucket_lambdas/packages/`:**
- Purpose: Build output — zip files ready for S3 upload
- Generated: Yes (by Makefile `_package` target)
- Committed: No (gitignored)

**`lambda_crons/install_venv/` and `lambda_crons/deploy_venv/`:**
- Purpose: Separate virtualenvs — `install_venv` for packaging Lambda dependencies, `deploy_venv` for running `deploy.py`
- Generated: Yes (by `make install_venv` / `make deploy_venv`)
- Committed: No

**`esphome/.esphome/`:**
- Purpose: ESPHome build artifacts, PlatformIO compiled binaries
- Generated: Yes (by `esphome compile`)
- Committed: No (gitignored per `esphome/.gitignore`)

**`human_benchmark/venv/`:**
- Purpose: Local Python virtual environment for desktop automation dependencies
- Generated: Yes
- Committed: No

**`.planning/codebase/`:**
- Purpose: GSD-generated codebase analysis documents
- Generated: Yes (by `/gsd-map-codebase`)
- Committed: Yes

---

*Structure analysis: 2026-06-26*
