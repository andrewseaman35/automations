import boto3


class LambdaHandler():
    sns_arn = 'arn:aws:sns:us-east-1:560983357304:lambda_crons'
    sns_client = boto3.client('sns')

    @classmethod
    def _run(cls, event, context):
        raise NotImplementedError()

    @classmethod
    def handle(cls, event, context):
        return cls._run(event, context)

    @classmethod
    def send_sns(cls, subject, content):
        cls.sns_client.publish(
            TopicArn=cls.sns_arn,
            Subject=subject,
            Message=content,
        )


def lambda_handler(event, context):
    return LambdaHandler.handle(event, context)
