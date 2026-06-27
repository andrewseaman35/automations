import hashlib
import hmac
import os

from webhook_lib.webhook_handler import SignatureVerificationError, WebhookHandler


class GithubWebhookHandler(WebhookHandler):
    """Handles GitHub webhook deliveries.

    Reference implementation for the webhook base: verifies the
    `X-Hub-Signature-256` HMAC, dispatches on the `X-GitHub-Event` header,
    and sends an SNS notification for events we care about.
    """

    sns_subject = "GitHub Webhook"

    # Env var (set by SAM) holding the name of the SSM parameter that stores
    # the webhook's shared secret.
    secret_param_env_var = "GITHUB_WEBHOOK_SECRET_PARAM"

    # Events worth a notification. Everything else is acknowledged silently.
    notify_events = {"push", "pull_request", "issues"}

    def verify_signature(self, raw_body, headers):
        signature = headers.get("x-hub-signature-256")
        if not signature:
            raise SignatureVerificationError("Missing X-Hub-Signature-256 header")
        secret = self._webhook_secret().encode("utf-8")
        expected = "sha256=" + hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise SignatureVerificationError("Signature mismatch")

    def _webhook_secret(self):
        param_name = os.environ[self.secret_param_env_var]
        return self.get_parameter(param_name)

    def _handle_webhook(self, payload, headers):
        event_type = headers.get("x-github-event", "unknown")
        delivery = headers.get("x-github-delivery", "")
        print(f"GitHub event={event_type} delivery={delivery}")

        if event_type in self.notify_events:
            self.notify(f"{self.sns_subject}: {event_type}", self._summarize(event_type, payload))

        return {"ok": True, "event": event_type}

    @staticmethod
    def _summarize(event_type, payload):
        repo = (payload.get("repository") or {}).get("full_name", "?")
        sender = (payload.get("sender") or {}).get("login", "?")
        if event_type == "push":
            ref = payload.get("ref", "?")
            count = len(payload.get("commits", []))
            return f"{sender} pushed {count} commit(s) to {ref} in {repo}"
        if event_type == "pull_request":
            action = payload.get("action", "?")
            title = (payload.get("pull_request") or {}).get("title", "?")
            return f"{sender} {action} a pull request in {repo}: {title}"
        if event_type == "issues":
            action = payload.get("action", "?")
            title = (payload.get("issue") or {}).get("title", "?")
            return f"{sender} {action} an issue in {repo}: {title}"
        return f"{event_type} from {sender} in {repo}"


# Module-level singleton; reused across warm invocations.
_handler = GithubWebhookHandler()


def lambda_handler(event, context):
    return _handler.handle(event, context)
