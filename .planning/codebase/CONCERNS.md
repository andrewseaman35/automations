# Codebase Concerns

**Analysis Date:** 2026-06-26

## Tech Debt

**Severely outdated Lambda dependencies:**
- Issue: `lambda_crons/base/requirements.txt` pins packages from 2018: `boto3==1.9.47`, `Jinja2==2.10.1`, `requests==2.20.1`, `urllib3==1.24.2`, `botocore==1.12.47`. These are 7+ years old and carry known CVEs.
- Files: `lambda_crons/base/requirements.txt`
- Impact: Security vulnerabilities in transitive dependencies; incompatibility with newer AWS APIs; blocks use of any modern Python features
- Fix approach: Upgrade to current pinned versions; use `pip-compile` or `uv` to generate a locked requirements file from unpinned top-level deps

**EOL Python 3.7 Lambda runtimes:**
- Issue: `lambda_crons` function configs all specify `runtime: python3.7`, which reached AWS end-of-life in November 2023.
- Files: `lambda_crons/patent_number/config.yml`, `lambda_crons/traffic_ticket/config.yml`, `lambda_crons/salt_level_entry_checker/config.yml`
- Impact: AWS no longer updates this runtime; functions may be force-deprecated; no security patches
- Fix approach: Update all `runtime` fields to `python3.12` and redeploy

**Duplicated base infrastructure across two Lambda families:**
- Issue: `lambda_crons/base/lambda_handler_base.py` and `s3_bucket_lambdas/base/lambda_handler_base.py` are near-identical with minor divergences (the s3 version added a `print(event)` debug statement and slightly different `_handle_error` copy). Each family also has its own `deploy.py`, `invoke.py`, and `Makefile`. Any cross-cutting fix must be applied in multiple places.
- Files: `lambda_crons/base/lambda_handler_base.py`, `s3_bucket_lambdas/base/lambda_handler_base.py`, `lambda_crons/deploy.py`, `s3_bucket_lambdas/deploy.py`
- Impact: Bug fixes and improvements must be duplicated; divergence will grow over time
- Fix approach: Extract a shared `base/` library at the repo root; have both families depend on it

**`test_find.py` duplicates production module code:**
- Issue: `human_benchmark/test_find.py` reimplements `BoundingBox`, `Screen`, `Sequence`, `find_white_contours`, and `find_center_of_contour` inline rather than importing from the production modules. It is also not an automated test — it is a runnable script.
- Files: `human_benchmark/test_find.py`
- Impact: Any changes to `screen.py` or `util.py` are not reflected here; creates a maintenance split
- Fix approach: Delete `test_find.py` and replace with imports from the actual modules, or convert to a proper pytest test

**`s3_bucket_lambdas/deploy.py` imports inside a method:**
- Issue: `import time` appears inside `_run()` at line 272 rather than at the top of the file.
- Files: `s3_bucket_lambdas/deploy.py` line 272
- Impact: Minor style violation; hides dependencies; confusing to readers
- Fix approach: Move `import time` to the top of the file (it is already imported implicitly via stdlib)

## Known Bugs

**Date range label always uses start year twice:**
- Symptoms: The summary CSV row labeled "Date" emits `start_year-start_year` (e.g. `2024-2024`) instead of `start_year-end_year`.
- Files: `expense_categorization/categorize.py` line 248
- Trigger: Every run; the comment in the source code acknowledges it: `# this is wrong`
- Workaround: Manually correct the generated CSV

**Duplicate `trigger_bucket` validation check:**
- Symptoms: `validate_config()` checks `if not self.config.get('trigger_bucket')` twice with identical bodies. The second check never raises a different error, so the intended second validation (likely `trigger_prefix`) is silently skipped.
- Files: `s3_bucket_lambdas/deploy.py` lines 104–107
- Trigger: Deploying an S3-triggered function without the `trigger_prefix` key
- Workaround: Manually ensure `trigger_prefix` is set in config

**Typo in error message:**
- Symptoms: `validate_config()` raises `ValueError(f"even_type {event_type} not supported")` — "even_type" should be "event_type".
- Files: `s3_bucket_lambdas/deploy.py` line 102
- Trigger: Providing an unsupported `event_type` in a config

**Swapped x/y coordinates in `find_window` rectangle:**
- Symptoms: `cv2.rectangle` is called with `(alignment_rec.top, alignment_rec.left)` as the first point. In OpenCV, coordinates are `(x, y)` — `left` is x and `top` is y. The arguments are transposed, so the preview rectangle is drawn in the wrong position.
- Files: `human_benchmark/screen.py` lines 48–53
- Trigger: Every call to `Screen.find_window()`

**Wrong module referenced in `__main__` help text:**
- Symptoms: `mame_high_score/lambda_handler.py` prints `python invoke.py salt_level_entry_checker --local` in its `__main__` block instead of `mame_high_score`.
- Files: `s3_bucket_lambdas/mame_high_score/lambda_handler.py` line 44
- Trigger: Running the file directly

## Security Considerations

**WiFi credentials committed to git:**
- Risk: SSID `Cooper` and passwords (`WalrusCactusMoneybags`, `MjfMERD82SHx`) are in plain text across all five ESPHome YAML files.
- Files: `esphome/fiat_lights.yaml`, `esphome/gdtest.yaml`, `esphome/garage_door.yaml`, `esphome/garage_door_lock.yaml`, `esphome/living_room_fan.yaml` (lines 19–25 in each)
- Current mitigation: The repo appears to be private; no `.gitignore` entry covers these files
- Recommendations: Use ESPHome `secrets.yaml` with a `!secret` substitution; add `secrets.yaml` to `.gitignore`; rotate the committed passwords

**AWS account ID hardcoded in source:**
- Risk: Account ID `560983357304` is embedded in SNS ARNs and IAM role ARNs across multiple files. If the repo is ever made public, it leaks an account identifier usable for reconnaissance.
- Files: `lambda_crons/base/lambda_handler_base.py` line 9, `s3_bucket_lambdas/base/lambda_handler_base.py` line 9, `salt_level/lambdas/salt_level_notification/lambda_handler.py` line 14, `lambda_crons/deploy.py` line 22, `s3_bucket_lambdas/deploy.py` line 20
- Current mitigation: None
- Recommendations: Move ARNs and account ID to environment variables or SSM; parameterise the deploy scripts

**Unencrypted HTTP for external API calls:**
- Risk: `traffic_ticket/lambda_handler.py` fetches an authentication token and submits a driver license number + date of birth over plain HTTP.
- Files: `lambda_crons/traffic_ticket/lambda_handler.py` lines 9–10
- Current mitigation: None — PII is in transit unencrypted
- Recommendations: Switch to HTTPS endpoints; if the upstream API does not offer HTTPS, add a note and consider discontinuing use

**No HTTP response status validation:**
- Risk: All lambda handlers call `requests.get/post` and immediately call `.json()` on the result without checking `response.status_code` or calling `response.raise_for_status()`. A 4xx or 5xx response body that happens to parse as JSON will be silently treated as valid data.
- Files: `lambda_crons/patent_number/lambda_handler.py` lines 78–84, `lambda_crons/traffic_ticket/lambda_handler.py` lines 25–39
- Current mitigation: `traffic_ticket` checks for a `data` key as a proxy; `patent_number` does no validation
- Recommendations: Call `response.raise_for_status()` before parsing

**Debug `print(event)` left in production code:**
- Risk: The entire Lambda event payload (which may contain sensitive SSM parameter values or S3 object metadata) is printed to CloudWatch on every invocation.
- Files: `s3_bucket_lambdas/base/lambda_handler_base.py` line 15
- Current mitigation: Log access is restricted to AWS IAM
- Recommendations: Remove the debug print or replace with structured logging at DEBUG level

## Performance Bottlenecks

**Unthrottled screen capture loop:**
- Problem: `Screen.capture()` in `screen.py` yields frames as fast as the CPU allows with no sleep or frame-rate cap. `reactiontime.py` and `sequence.py` run this loop continuously.
- Files: `human_benchmark/screen.py` lines 63–66, `human_benchmark/reactiontime.py` lines 34–45, `human_benchmark/sequence.py` lines 24–33
- Cause: No `cv2.waitKey` or `time.sleep` in the capture generator itself
- Improvement path: Add a configurable frame delay (e.g., `cv2.waitKey(16)` for ~60 fps) inside `capture()`

**Hardcoded 15-second sleep during S3 deploy:**
- Problem: `s3_bucket_lambdas/deploy.py` sleeps for 15 seconds unconditionally to wait for Lambda function propagation before attaching S3 notifications.
- Files: `s3_bucket_lambdas/deploy.py` lines 272–273
- Cause: Polling workaround; no retry loop or status check
- Improvement path: Poll `get_function` until state is `Active`, then proceed; use exponential backoff

## Fragile Areas

**Brittle CSV parsing in expense categorization:**
- Files: `expense_categorization/categorize.py` line 176
- Why fragile: `Transaction(*line.split(','))` splits on every comma. Chase CSV descriptions frequently contain commas (e.g. `"WHOLEFDS MKT #10, AUSTIN TX"`), which breaks the positional argument count and raises `TypeError`.
- Safe modification: Replace with Python's `csv.reader` for proper quoted-field handling
- Test coverage: None

**Brittle application number extraction:**
- Files: `lambda_crons/patent_number/lambda_handler.py` line 87
- Why fragile: `payload['searchText'].split('(')[1].split(')')[0]` extracts the application number via substring manipulation of the search query string. Any change to the payload format silently returns a wrong or empty string.
- Safe modification: Store the application number as a separate constant; avoid parsing it from a query string

**No input validation for category selection:**
- Files: `expense_categorization/categorize.py` lines 104–105
- Why fragile: `category_inputs[str(inp)]` raises a bare `KeyError` if the user types an out-of-range number, a letter, or presses Enter. The program crashes with a traceback mid-session.
- Safe modification: Wrap in a loop with input validation before dictionary lookup

**DynamoDB state builder only supports `str` and `bool`:**
- Files: `lambda_crons/base/state_lambda_handler_base.py` lines 22–29
- Why fragile: `build_state_from_result` raises `TypeError` for any non-string, non-bool value (int, float, list, None). Adding a new numeric field to a lambda result will crash the state write.
- Safe modification: Add cases for `int` (`N` type) and `NoneType`

**`reactiontime.py` crashes on unexpected screen color:**
- Files: `human_benchmark/reactiontime.py` line 45
- Why fragile: If any pixel in the bounding box is not classified as blue, green, or red, the program raises `Exception("No known colors found!")` and terminates. Any transient animation or tooltip causes a crash.
- Safe modification: Log and `continue` instead of raising; only raise after N consecutive unrecognized frames

## Missing Critical Features

**`create_s3_event_trigger` is a copy of `create_cron_event_trigger`:**
- Problem: `s3_bucket_lambdas/deploy.py` defines `create_s3_event_trigger` at line 161 with an identical body to `create_cron_event_trigger`. It tries to create an EventBridge scheduled rule for an S3-triggered function, which is incorrect — S3 event triggers use `put_bucket_notification_configuration`, not EventBridge schedule rules.
- Blocks: The S3 deploy path (`EVENT_TYPE_S3`) never calls `create_s3_event_trigger` (it calls `put_bucket_notification_configuration` directly in `_run()`), so the method is dead code — but its existence is misleading.
- Files: `s3_bucket_lambdas/deploy.py` lines 161–166

**No retry logic for external HTTP calls:**
- Problem: Both `patent_number` and `traffic_ticket` lambda handlers make a single HTTP call with no retry on transient failures (network blips, 5xx responses). A single failed request causes the handler to raise, which triggers the SNS error notification.
- Files: `lambda_crons/patent_number/lambda_handler.py` lines 78–84, `lambda_crons/traffic_ticket/lambda_handler.py` lines 25–38

## Test Coverage Gaps

**No automated tests for any lambda function:**
- What's not tested: `_run()` logic, DynamoDB state building, SNS content rendering, error handling paths
- Files: All files under `lambda_crons/*/lambda_handler.py` and `s3_bucket_lambdas/*/lambda_handler.py`
- Risk: Logic regressions in categorization, state diffing, or template rendering go undetected until production
- Priority: High

**No automated tests for expense categorization:**
- What's not tested: CSV parsing, category matching, search term conflict detection, output file format
- Files: `expense_categorization/categorize.py`
- Risk: The known date-range bug and CSV comma-splitting bug have no regression tests
- Priority: Medium

**`human_benchmark` has no real tests:**
- What's not tested: Color detection thresholds, contour finding, coordinate calculations
- Files: `human_benchmark/util.py`, `human_benchmark/screen.py`
- Risk: Color range constants tuned for one display will silently fail on different monitors or lighting
- Priority: Low

---

*Concerns audit: 2026-06-26*
