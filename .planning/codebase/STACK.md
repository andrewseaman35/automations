# Technology Stack

**Analysis Date:** 2026-06-26

## Languages

**Primary:**
- Python 3.7–3.9 - AWS Lambda functions (all `lambda_crons/` and `s3_bucket_lambdas/` handlers)
- Python 3.x (local) - Desktop automation scripts (`human_benchmark/`, `expense_categorization/`)

**Secondary:**
- C/C++ (Arduino) - Embedded hardware sensor firmware (`salt_level/salt_level_sensor/salt_level_sensor.ino`, `garage_door_lock/garage_door_lock.ino`)
- YAML - ESPHome device configuration (`esphome/*.yaml`)

## Runtime

**Environment:**
- AWS Lambda (Python 3.7 for `lambda_crons/`, Python 3.9 for `s3_bucket_lambdas/`)
- macOS desktop for local automation scripts (`human_benchmark/`, `expense_categorization/`)
- Arduino-compatible microcontrollers (ESP8266 / MKR WiFi boards) for IoT firmware

**Package Manager:**
- pip (Python) — no top-level `requirements.txt`; each lambda subdirectory inherits from its `base/requirements.txt`
- Lockfile: not present (pinned versions in requirements files only)

## Frameworks

**Core (Lambda functions):**
- boto3 `1.9.47` / botocore `1.12.47` - AWS SDK for Python; all Lambda handlers use this to call DynamoDB, SNS, SSM, S3, CloudWatch Events, and Lambda APIs
- Jinja2 `2.10.1` - SNS notification templating; base handlers load `.jinja2` templates from the function directory
- requests `2.20.1` - HTTP client used by `patent_number` and `traffic_ticket` lambdas

**Desktop Automation (`human_benchmark/`):**
- pyautogui - Mouse/keyboard control for simulating browser game interactions
- opencv-python (cv2) - Computer vision; screen capture analysis, HSV color detection, contour finding
- numpy - Array processing for image analysis
- mss - Fast screen capture

**Build/Deploy:**
- PyYAML - Parsed in `deploy.py` scripts to load `config.yml` per function
- argparse (stdlib) - CLI argument parsing in `deploy.py` and `invoke.py`
- Makefile + subprocess - `deploy.py` shells out to `make` for packaging steps

**ESPHome (IoT):**
- ESPHome framework - Generates C++ firmware from YAML for ESP8266 D1 boards; handles WiFi, OTA, Home Assistant API integration
- PlatformIO - Underlying build system (compiled artifacts in `esphome/.esphome/build/`)

**Arduino Libraries (salt level sensor):**
- ArduinoBearSSL - TLS client for MQTT over SSL
- ArduinoECCX08 - Hardware crypto chip integration (ATECC508A/608A)
- ArduinoMqttClient - MQTT protocol client
- ArduinoJson - JSON serialization for sensor payloads
- WiFiNINA - WiFi connectivity for Arduino MKR WiFi boards
- NewPing - Ultrasonic distance sensor (HC-SR04) driver

## Key Dependencies

**Critical:**
- `boto3==1.9.47` - Every Lambda and deploy script depends on this; pinned to an old version; see `lambda_crons/base/requirements.txt` and `s3_bucket_lambdas/base/requirements.txt`
- `Jinja2==2.10.1` - Required by base lambda handler classes for SNS content rendering
- `requests==2.20.1` - Required by `patent_number` and `traffic_ticket` lambda handlers

**Infrastructure:**
- `python-dateutil==2.7.5` - Date parsing in `patent_number` and `salt_level_entry_checker`
- `s3transfer==0.1.13` - Dependency of boto3 for S3 file uploads

## Configuration

**Environment:**
- Lambda functions are configured per-function via `config.yml` (runtime, handler, S3 bucket/key, schedule expressions, trigger type)
- Secrets stored in AWS SSM Parameter Store; retrieved at runtime via `get_parameter()` in the base handler class
- Local invocation supports `--take-input` flag (prompts for SSM values), or falls back to environment variables

**Build:**
- `lambda_crons/deploy.py` - CLI tool for cron-triggered lambdas; reads `config.yml`, packages via `make`, uploads to S3, creates/updates Lambda + CloudWatch Events
- `s3_bucket_lambdas/deploy.py` - CLI tool for S3-event-triggered lambdas; same pattern plus S3 bucket notification configuration
- ESPHome build artifacts in `esphome/.esphome/build/fiat_light/` (PlatformIO-managed, not committed)

## Platform Requirements

**Development:**
- Python 3.7+ for lambda development and deploy tooling
- Python 3.x + pyautogui + opencv-python + mss + numpy for `human_benchmark/` scripts (macOS)
- ESPHome CLI for compiling and flashing IoT device configs
- Arduino IDE or PlatformIO for `.ino` firmware files
- AWS CLI profile configured for deploy scripts (`--profile` flag supported)

**Production:**
- AWS Lambda (us-east-1) — primary execution environment
- ESP8266 D1 microcontrollers running ESPHome firmware
- Arduino MKR WiFi (or similar) board running salt level sensor firmware
- AWS IoT (MQTT broker at port 8883) for salt level sensor data ingestion

---

*Stack analysis: 2026-06-26*
