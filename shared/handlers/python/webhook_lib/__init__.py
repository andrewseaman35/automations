"""Shared Lambda handler base classes, packaged as a Lambda layer.

At runtime this lives at `/opt/python/webhook_lib`, so functions import it as
`from webhook_lib.webhook_handler import WebhookHandler`.
"""
