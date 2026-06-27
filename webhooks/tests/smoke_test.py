"""Pure-Python smoke test for the webhook handlers.

Exercises the real handler classes end-to-end (signature verification,
parsing, dispatch, response shape) without AWS or the SAM CLI. Run with:

    python3 webhooks/tests/smoke_test.py
"""

import hashlib
import hmac
import json
import os
import sys

# Make the layer code importable the same way Lambda does (/opt/python).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO_ROOT, "shared", "handlers", "python"))
sys.path.insert(0, os.path.join(REPO_ROOT, "webhooks", "functions", "github"))

SECRET = "test-secret"
SECRET_PARAM = "/webhooks/github/secret"

# Route the handler's SSM lookup to an env var via local mode.
os.environ["GITHUB_WEBHOOK_SECRET_PARAM"] = SECRET_PARAM
os.environ[SECRET_PARAM] = SECRET

import app  # noqa: E402  (import after sys.path / env setup)


def _sign(body_bytes):
    return "sha256=" + hmac.new(SECRET.encode(), body_bytes, hashlib.sha256).hexdigest()


def _event(body, signature, event_type="push"):
    body_str = json.dumps(body)
    return {
        "version": "2.0",
        "headers": {
            "content-type": "application/json",
            "x-github-event": event_type,
            "x-github-delivery": "test-delivery",
            **({"x-hub-signature-256": signature} if signature else {}),
        },
        # `_local` keeps the handler in local mode: get_parameter falls back to
        # the env var above instead of calling SSM.
        "_local": {"allow_aws": False},
        "body": body_str,
        "isBase64Encoded": False,
    }


def run():
    passed = 0
    failed = 0

    def check(name, cond):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}")

    push_body = {
        "ref": "refs/heads/main",
        "commits": [{"id": "a"}, {"id": "b"}],
        "repository": {"full_name": "andrewseaman35/automations"},
        "sender": {"login": "andrewseaman35"},
    }
    body_bytes = json.dumps(push_body).encode()

    # 1. Valid signature -> 200, dispatched.
    resp = app.lambda_handler(_event(push_body, _sign(body_bytes)), None)
    check("valid push returns 200", resp["statusCode"] == 200)
    check("valid push body echoes event", json.loads(resp["body"]) == {"ok": True, "event": "push"})

    # 2. Bad signature -> 401.
    resp = app.lambda_handler(_event(push_body, "sha256=deadbeef"), None)
    check("bad signature returns 401", resp["statusCode"] == 401)

    # 3. Missing signature header -> 401.
    resp = app.lambda_handler(_event(push_body, None), None)
    check("missing signature returns 401", resp["statusCode"] == 401)

    # 4. Valid signature but invalid JSON -> 400.
    bad = "{not json".encode()
    evt = _event(push_body, _sign(bad))
    evt["body"] = "{not json"
    resp = app.lambda_handler(evt, None)
    check("invalid JSON returns 400", resp["statusCode"] == 400)

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
