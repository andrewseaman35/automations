import base64
import json
import os
import traceback

from webhook_lib.base_handler import BaseHandler


class WebhookError(Exception):
    """A webhook-handling error that maps to an HTTP status code."""

    status_code = 400


class SignatureVerificationError(WebhookError):
    status_code = 401


class WebhookHandler(BaseHandler):
    """Base for API Gateway HTTP API (payload format 2.0) webhook lambdas.

    Subclasses implement `_handle_webhook(payload, headers)` and usually
    override `verify_signature`. The lifecycle:
      1. parse the HTTP request (headers + raw body)
      2. verify the signature (raises SignatureVerificationError -> 401)
      3. parse the payload (JSON by default)
      4. dispatch to `_handle_webhook`
      5. always return a well-formed API Gateway response dict

    To add a new webhook, subclass this, set the signature scheme, implement
    `_handle_webhook`, and wire a new POST route in `webhooks/template.yaml`.
    """

    success_status_code = 200

    # Local-testing escape hatch: when WEBHOOK_SKIP_SIGNATURE=true, signature
    # verification is bypassed. NEVER set this in a deployed environment.
    skip_signature_env_var = "WEBHOOK_SKIP_SIGNATURE"

    def _before_run(self, event, context):
        super()._before_run(event, context)
        self.headers = self._normalize_headers(event.get("headers") or {})
        self.raw_body = self._extract_body(event)
        self.request_context = event.get("requestContext", {})

    def _run(self, event, context):
        if os.environ.get(self.skip_signature_env_var) != "true":
            self.verify_signature(self.raw_body, self.headers)
        payload = self.parse_payload(self.raw_body)
        return self._handle_webhook(payload, self.headers)

    def _after_run(self, result):
        # A subclass may return a ready-made response dict, or just a body.
        if isinstance(result, dict) and "statusCode" in result:
            return result
        return self._response(self.success_status_code, result)

    def _handle_error(self, e):
        status = getattr(e, "status_code", 500)
        if status >= 500:
            # Unexpected failure: log + notify like the base does.
            traceback.print_exc()
            self.notify(self.sns_subject_error, f"{self.__class__.__name__} failed:\n{e}")
        else:
            print(f"{self.__class__.__name__} rejected request ({status}): {e}")
        return self._response(status, {"error": str(e)})

    # --- request parsing -------------------------------------------------

    @staticmethod
    def _normalize_headers(headers):
        # HTTP API v2 already lowercases header names, but be defensive so
        # `sam local` and hand-written test events behave the same.
        return {k.lower(): v for k, v in headers.items()}

    @staticmethod
    def _extract_body(event):
        """Return the raw request body as bytes (needed for HMAC checks)."""
        body = event.get("body") or ""
        if event.get("isBase64Encoded"):
            return base64.b64decode(body)
        return body.encode("utf-8") if isinstance(body, str) else body

    # --- overridable hooks ----------------------------------------------

    def verify_signature(self, raw_body, headers):
        """Verify the request is authentic. Default: no verification.

        Override and raise `SignatureVerificationError` on mismatch.
        """
        return None

    def parse_payload(self, raw_body):
        """Parse the raw body into a Python object. Default: JSON."""
        if not raw_body:
            return {}
        try:
            return json.loads(raw_body)
        except (ValueError, TypeError) as e:
            raise WebhookError(f"Invalid JSON body: {e}")

    def _handle_webhook(self, payload, headers):
        raise NotImplementedError

    # --- response building ----------------------------------------------

    @staticmethod
    def _response(status_code, body):
        if isinstance(body, (dict, list)):
            content_type = "application/json"
            body = json.dumps(body)
        else:
            content_type = "text/plain"
            body = "" if body is None else str(body)
        return {
            "statusCode": status_code,
            "headers": {"content-type": content_type},
            "body": body,
        }
