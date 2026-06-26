# Testing Patterns

**Analysis Date:** 2026-06-26

## Test Framework

**Runner:** None — no test framework is installed or configured in this repository.

- No `pytest`, `unittest`, `nose`, or any other test runner detected
- No `pytest.ini`, `setup.cfg [tool:pytest]`, `pyproject.toml [tool.pytest]`, or `jest.config.*` files present
- No test runner invocation in any `Makefile` reviewed

**Assertion Library:** None (no formal assertions outside of production code)

**Run Commands:**
```bash
# No test commands defined — no test runner configured
```

## Test File Organization

**Location:** There is one file named `test_find.py` at `human_benchmark/test_find.py`. Despite the `test_` prefix, this is NOT a formal test suite — it is an exploratory prototype/script that imports libraries and runs automation code directly. It contains no test functions, no assertions, and no test framework imports.

**Naming:**
- The `test_find.py` naming convention is misleading; the file is a development scratch script, not a test file

**Structure:**
```
human_benchmark/
└── test_find.py      # exploratory script, NOT a test suite
```

## Test Structure

**Suite Organization:** Not applicable — no test suites exist.

**Patterns:** None defined.

## Mocking

**Framework:** None

**Patterns:** No mocking infrastructure exists. Lambda handlers interact with live AWS services (boto3 clients for SNS, SSM, DynamoDB) and have no seams for injecting test doubles.

**What to Mock (if tests were added):**
- `boto3.session.Session` and all derived clients (`sns_client`, `ssm_client`, `ddb_client`)
- File I/O in `expense_categorization/categorize.py` (`open(CONFIG_FILE_NAME)`)
- `requests.post` in `lambda_crons/patent_number/lambda_handler.py`
- `pyautogui` calls and `mss()` screen capture in `human_benchmark/` scripts

## Fixtures and Factories

**Test Data:** None — no fixture files, factory functions, or test data helpers exist in the project.

**Location:** No `fixtures/`, `factories/`, or `conftest.py` files present.

## Coverage

**Requirements:** None enforced — no coverage tooling configured.

**View Coverage:**
```bash
# Not configured
```

## Test Types

**Unit Tests:** Not present.

**Integration Tests:** Not present.

**E2E Tests:** Not present. The `human_benchmark/` scripts (e.g., `reactiontime.py`, `sequence.py`) perform live screen automation but are not test suites — they are the automation scripts themselves.

## Validation Approaches (In-Production Code)

The codebase uses two in-production validation patterns as a substitute for tests:

**1. Assertions for data invariants** (`expense_categorization/categorize.py`):
```python
def validate_file_dates(parsed_filenames):
    assert len(set(start_dates)) == 1, 'multiple start_dates: {}'.format(start_dates)
    assert len(set(end_dates)) == 1, 'multiple end_dates: {}'.format(end_dates)
```

**2. Config validation with `ValueError`** (`s3_bucket_lambdas/deploy.py`, `lambda_crons/deploy.py`):
```python
def validate_config(self):
    if 'code' not in self.config:
        raise ValueError('`code` must be defined')
    if event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError(f"even_type {event_type} not supported")
```

**3. Top-level Lambda error catching** (`s3_bucket_lambdas/base/lambda_handler_base.py`):
```python
def handle(self, event, context):
    try:
        self._before_run(event)
        result = self._run(event, context)
        self._after_run(result)
    except Exception as e:
        self._handle_error(e)
        traceback.print_exc()
```
This catches all runtime errors and routes them to SNS notification.

## Test Coverage Gaps

**Entire codebase:**
- What's not tested: All production code — Lambda handlers, deploy scripts, screen automation, expense categorization
- Files: `lambda_crons/`, `s3_bucket_lambdas/`, `expense_categorization/categorize.py`, `human_benchmark/`
- Risk: Lambda handler logic changes (e.g., `_run` overrides, `build_content_from_result`) can silently break without any automated signal
- Priority: High for Lambda handlers; Medium for deploy scripts; Low for interactive scripts

**Lambda handler base classes:**
- Files: `lambda_crons/base/lambda_handler_base.py`, `s3_bucket_lambdas/base/lambda_handler_base.py`
- What's not tested: lifecycle orchestration (`handle` → `_before_run` → `_run` → `_after_run`), error routing to SNS, `get_parameter` fallback logic
- Risk: Base class changes break all derived handlers simultaneously

**Config validation:**
- Files: `s3_bucket_lambdas/deploy.py`, `lambda_crons/deploy.py`
- What's not tested: `validate_config` edge cases (missing keys, unsupported event types, missing `{nonce}`)
- Risk: Deploy misconfiguration reaches AWS API calls before being caught

## Guidance for Adding Tests

If tests are introduced, the following setup is recommended:

**Framework:** `pytest` — install with `pip install pytest pytest-mock`

**Structure:**
```
<module>/
├── lambda_handler.py
└── tests/
    └── test_lambda_handler.py
```

**Minimal pattern for a Lambda handler test:**
```python
import pytest
from unittest.mock import MagicMock, patch

def test_run_processes_records():
    handler = MAMEHighScoreLambdaHandler()
    event = {"Records": [{"eventName": "ObjectCreated:Put", "s3": {"object": {"key": "hi/score.hi"}}}]}
    result = handler._run(event, context=None)
    assert result == {"changes": ["score.hi"]}
```

**Key mocking targets:**
- `boto3.session.Session` — mock at `boto3.session.Session` to avoid live AWS calls
- `jinja2.Environment.get_template` — mock to avoid filesystem template loading

---

*Testing analysis: 2026-06-26*
