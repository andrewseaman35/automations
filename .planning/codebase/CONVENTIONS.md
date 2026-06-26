# Coding Conventions

**Analysis Date:** 2026-06-26

## Naming Patterns

**Files:**
- `snake_case.py` for all Python modules: `lambda_handler.py`, `lambda_handler_base.py`, `categorize.py`
- `test_*.py` prefix for exploratory/prototype scripts (not formal test suites): `human_benchmark/test_find.py`
- Descriptive suffixes: `_base.py` for base classes, `_handler.py` for handlers

**Classes:**
- `PascalCase` throughout: `LambdaHandler`, `StateLambdaHandler`, `MAMEHighScoreLambdaHandler`, `BoundingBox`, `Config`, `Transaction`, `Deploy`
- Concrete handler classes follow the pattern `<Domain>LambdaHandler` inheriting from a base

**Functions and Methods:**
- `snake_case` for all functions and methods: `parse_filename`, `load_transactions`, `find_center_of_contour`
- Private/internal methods prefixed with a single underscore: `_parse_event`, `_init_aws`, `_before_run`, `_run`, `_after_run`, `_handle_error`
- Abstract/overrideable methods also use `_` prefix: `_run` is defined as `raise NotImplementedError()` in base classes

**Variables:**
- `snake_case` for local and instance variables
- Instance variables set in `__init__` or `_parse_event`: `self.is_local`, `self.aws_profile`, `self.sns_client`
- Module-level singletons use a leading underscore: `_config = Config(CONFIG_FILE_NAME)` in `expense_categorization/categorize.py`

**Constants:**
- `UPPER_SNAKE_CASE` for module-level constants: `CREATION_EVENT_NAME`, `ACTION_CREATE`, `S3_BUCKET`, `DEFAULT_AWS_REGION`, `FILENAME_REGEX`
- Class-level configuration constants use `snake_case` (treated as overrideable class attributes, not strict constants): `sns_arn`, `sns_subject_template`, `sns_template_filename` in `lambda_crons/base/lambda_handler_base.py` and `s3_bucket_lambdas/base/lambda_handler_base.py`

## Code Style

**Formatting:**
- No automated formatter configured (no `.prettierrc`, no `pyproject.toml` with black/ruff, no `.flake8`)
- 4-space indentation used consistently in all project files
- Blank lines between top-level definitions; occasional inconsistency within files (e.g., missing blank line between `sct = mss()` and the first `@dataclass` in `screen.py`)

**Quote Style:**
- Mixed usage across the codebase: single quotes dominant in `s3_bucket_lambdas/deploy.py` and `lambda_crons/deploy.py`; double quotes dominant in `lambda_crons/` handler files and `s3_bucket_lambdas/` handler files
- f-strings and `.format()` both used; no single standard: `f"Created: {function_arn}"` alongside `'{}:::{}'.format(S3_BUCKET, key)`

**Type Hints:**
- Used sparingly; not enforced
- Return type hints on dataclass methods: `def to_dict(self) -> dict`, `def capture(self)` (missing)
- Parameter type hints used in newer files: `def __init__(self, bounding_box: BoundingBox) -> None` in `human_benchmark/screen.py`; `def find_window(self, alignment_rec: BoundingBox | None)` uses Python 3.10+ union syntax
- No `mypy` or type-checking tooling detected

**Dataclasses:**
- Used for simple value objects: `BoundingBox` and `Point` in `human_benchmark/screen.py` and `human_benchmark/util.py`
- Import: `from dataclasses import dataclass`

## Import Organization

**Order observed:**
1. Standard library imports (alphabetical within group)
2. Blank line
3. Third-party package imports
4. Blank line
5. Local/relative imports

**Example from `human_benchmark/reactiontime.py`:**
```python
from time import sleep          # stdlib

import pyautogui                # third-party
import numpy as np
import cv2

from screen import Screen, BoundingBox   # local
from util import hsv_has_color, Point
```

**Example from `lambda_crons/base/state_lambda_handler_base.py`:**
```python
import datetime                 # stdlib
import json

from .lambda_handler_base import LambdaHandler   # relative local import
```

**Path Aliases:**
- None configured; local imports use bare module names when running from the module's own directory (e.g., `from screen import Screen`) or relative imports within packages (e.g., `from .lambda_handler_base import LambdaHandler`)

## Error Handling

**Lambda base handler pattern** (`lambda_crons/base/lambda_handler_base.py`, `s3_bucket_lambdas/base/lambda_handler_base.py`):
```python
def handle(self, event, context):
    try:
        self._before_run(event)
        result = self._run(event, context)
        self._after_run(result)
    except Exception as e:
        print('Uh oh, error!')
        self._handle_error(e)
        traceback.print_exc()
```
- Top-level `except Exception` catches all errors; error details sent via SNS

**Validation raises `ValueError`** for config and input issues:
```python
raise ValueError('`code` must be defined')
raise ValueError(f"even_type {event_type} not supported")
raise ValueError("{} required, either add `--take-input` flag or add to ENV".format(name))
```

**Domain errors raise generic `Exception`:**
```python
raise Exception("No known colors found!")        # human_benchmark/reactiontime.py
raise Exception('repeated term in categorization: {}'.format(term))  # expense_categorization/categorize.py
```

**AWS ClientError handling** in deploy scripts (`s3_bucket_lambdas/deploy.py`, `lambda_crons/deploy.py`):
```python
try:
    response = self.events_client.describe_rule(Name=event_rule_name)
except ClientError as exception:
    if exception.response['Error']['Code'] == 'ResourceNotFoundException':
        return None
    raise exception
```

**Assertions** used for data validation in non-lambda code:
```python
assert len(set(start_dates)) == 1, 'multiple start_dates: {}'.format(start_dates)
```
Found in `expense_categorization/categorize.py`.

**Abstract method pattern:**
```python
def _run(self, event, context):
    raise NotImplementedError()
```
Used in both `lambda_crons/base/lambda_handler_base.py` and `s3_bucket_lambdas/base/lambda_handler_base.py`.

## Logging

**Framework:** `print()` — no logging library used anywhere in project code

**Patterns:**
- Debug output printed directly: `print(event)`, `print(changes)`, `print(result)`
- SNS notification for structured output from Lambda runs (subject + body template)
- Visual separators for important output blocks: `print("\n++++++++++++++\n")`
- No log levels, no structured logging, no timestamps in print output

## Comments

**When to Comment:**
- Inline comments explain non-obvious logic or intent: `# "Recent" in this context is within the last day`
- Comments on skipped branches: `# Skip deletion events. We shouldn't be deleting anyways..`
- Section markers in longer functions: `# Uploads the lambda function package to S3`
- Color constant annotations with RGB source values: `# BLUE = rgb(43, 135, 209)` in `human_benchmark/reactiontime.py`

**Docstrings:**
- Rarely used; present only on `Deploy` classes: `"""Command line tool to deploy ..."""`
- One method docstring in `human_benchmark/screen_position.py` (Portuguese-language comment)
- No consistent JSDoc/Google-style docstring convention across the codebase

## Function Design

**Size:** Functions are generally short and focused; longer methods exist in `Deploy` classes and `categorize.py`'s `run()` function

**Parameters:** Keyword arguments used for clarity when calling constructors: `Screen(bounding_box=self._bounding_box)`; deploy scripts use argparse for CLI parameters

**Return Values:**
- Lambda `_run()` methods return a plain `dict` with result data
- Utility functions return domain objects (`Point`, contours) or primitives
- Methods that produce side effects return `None` (implicit)

## Module Design

**Exports:** No `__all__` defined in any project module; all public names are importable

**Barrel Files:** Not used; imports are direct from specific modules

**Module-Level Execution:**
- Several scripts execute code at module level (not guarded by `if __name__ == '__main__'`): `sct = mss()` in `human_benchmark/screen.py`, `_config = Config(...)` in `expense_categorization/categorize.py`
- Lambda handler files use `if __name__ == '__main__':` guard with a "use invoke.py" message
- Standalone scripts (e.g., `color.py`, old `test_find.py`) run logic at module level with no guard

## Template Method Pattern

The dominant design pattern for Lambda handlers:

```python
# Base class defines the lifecycle
class LambdaHandler():
    def handle(self, event, context):     # entry point (do not override)
        self._before_run(event)           # setup (shared)
        result = self._run(event, context)  # override this
        self._after_run(result)           # teardown (shared)

# Subclass provides domain logic
class MAMEHighScoreLambdaHandler(LambdaHandler):
    def _run(self, event, context):       # only method to override
        ...
```

Class-level attributes are used to customize behavior in subclasses without overriding methods:
```python
class MAMEHighScoreLambdaHandler(LambdaHandler):
    sns_subject_template = "MAME High Score Update"   # overrides base class attribute
```

---

*Convention analysis: 2026-06-26*
