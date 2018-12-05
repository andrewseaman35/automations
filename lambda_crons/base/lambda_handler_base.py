import boto3


class LambdaHandler():
    sns_arn = 'arn:aws:sns:us-east-1:560983357304:lambda_crons'
    sns_subject_template = "Lambda Cron Update"
    sns_subject_error = "Lambda Cron Error!"

    sns_client = boto3.client('sns')
    ssm_client = boto3.client('ssm')

    @classmethod
    def _run(cls, event, context):
        raise NotImplementedError()

    @classmethod
    def handle(cls, event, context):
        try:
            result = cls._run(event, context)
            return result
        except Exception as e:
            print('Uh oh, error!')
            print(str(e))
            cls._handle_error(e)
        return None

    @classmethod
    def _handle_error(cls, e):
        content = 'Hello! Looks like your function failed...\n'
        content += 'Here\'s the exception: \n'
        content += '{}'.format(str(e))
        cls.send_sns(
            subject=cls.sns_subject_error,
            content=content,
        )

    @classmethod
    def get_parameter(cls, name):
        response = cls.ssm_client.get_parameter(Name=name)
        return response['Parameter']['Value']

    @classmethod
    def send_sns(cls, subject, content):
        print("Sending SNS: {}, {}".format(subject, content))
        cls.sns_client.publish(
            TopicArn=cls.sns_arn,
            Subject=subject,
            Message=content,
        )


def lambda_handler(event, context):
    return LambdaHandler.handle(event, context)
