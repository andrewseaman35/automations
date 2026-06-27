import os
import traceback

import boto3


class BaseHandler:
    """Generic AWS Lambda lifecycle: parse event -> run -> notify.

    Subclasses implement `_run(event, context)` and may override the
    `_before_run` / `_after_run` hooks. Any unhandled exception from `_run`
    is routed to `_handle_error`.

    This is the modern replacement for the old `lambda_crons` /
    `s3_bucket_lambdas` base classes. Key differences from the old design:
      * Nothing is hardcoded -- the SNS topic ARN is read from the
        environment (set by SAM) instead of being baked into the class.
      * boto3 clients are created lazily so unit tests don't need AWS.
      * Local/dev flags live under an explicit `_local` key in the event,
        keeping production API Gateway events untouched.
    """

    # Env var (set by the SAM template) holding an optional SNS topic ARN.
    # When unset, notifications are printed but not published.
    sns_topic_env_var = "NOTIFY_SNS_TOPIC_ARN"
    sns_subject = "Lambda Update"
    sns_subject_error = "Lambda Error!"

    def __init__(self):
        self.is_local = False
        self.allow_aws = True
        self.take_input = False
        self.aws_profile = None
        self._session = None
        self._sns_client = None
        self._ssm_client = None

    # --- lifecycle -------------------------------------------------------

    def handle(self, event, context):
        try:
            self._before_run(event, context)
            result = self._run(event, context)
            return self._after_run(result)
        except Exception as e:  # noqa: BLE001 - top-level catch-all is intentional
            return self._handle_error(e)

    def _before_run(self, event, context):
        self._parse_local_flags(event)

    def _run(self, event, context):
        raise NotImplementedError

    def _after_run(self, result):
        return result

    def _handle_error(self, e):
        traceback.print_exc()
        self.notify(self.sns_subject_error, f"{self.__class__.__name__} failed:\n{e}")
        # Re-raise so Lambda marks the invocation as failed (enables retries /
        # DLQ). Subclasses that must always return a value (e.g. webhooks)
        # override this method.
        raise

    # --- local/dev support ----------------------------------------------

    def _parse_local_flags(self, event):
        # Production triggers never include `_local`; we only set it when
        # invoking the handler ourselves for local testing.
        meta = event.get("_local", {}) if isinstance(event, dict) else {}
        self.is_local = bool(meta)
        self.allow_aws = meta.get("allow_aws", False) if self.is_local else True
        self.take_input = meta.get("take_input", False) if self.is_local else False
        self.aws_profile = meta.get("aws_profile") if self.is_local else None

    # --- aws helpers -----------------------------------------------------

    @property
    def session(self):
        if self._session is None:
            self._session = (
                boto3.session.Session(profile_name=self.aws_profile)
                if self.aws_profile
                else boto3.session.Session()
            )
        return self._session

    @property
    def sns_client(self):
        if self._sns_client is None:
            self._sns_client = self.session.client("sns")
        return self._sns_client

    @property
    def ssm_client(self):
        if self._ssm_client is None:
            self._ssm_client = self.session.client("ssm")
        return self._ssm_client

    @property
    def sns_topic_arn(self):
        return os.environ.get(self.sns_topic_env_var) or None

    def get_parameter(self, name, decrypt=True):
        """Read an SSM parameter. Falls back to env/stdin in local mode."""
        if self.allow_aws:
            resp = self.ssm_client.get_parameter(Name=name, WithDecryption=decrypt)
            return resp["Parameter"]["Value"]
        if self.is_local and self.take_input:
            return input(f"Value for SSM parameter {name}: ")
        value = os.environ.get(name)
        if not value:
            raise ValueError(
                f"{name} required from SSM; set the env var or pass take_input"
            )
        return value

    def notify(self, subject, message):
        topic_arn = self.sns_topic_arn
        suffix = "" if (self.allow_aws and topic_arn) else " (not sent)"
        print(f"--- SNS{suffix} ---\nSubject: {subject}\n{message}\n---")
        if self.allow_aws and topic_arn:
            self.sns_client.publish(TopicArn=topic_arn, Subject=subject, Message=message)
