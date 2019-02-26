import argparse
import os
import subprocess
import time
import yaml

from botocore.exceptions import ClientError
import boto3

TEMPLATE_FILE = '{root}/config/web_template.json'
OUTPUT_FILE = '{root}/website/js/config/config.js'

S3_BUCKET = 'aseaman-lambda-functions'
KEY_FORMAT = 'jobs/{function_name}_{nonce}.zip'

LOCAL_PATH_FORMAT = 'packages/{function_name}.zip'

DEFAULT_AWS_REGION = 'us-east-1'

DEFAULT_CONFIG = {
    'runtime': 'python3.7',
    'role': 'arn:aws:iam::560983357304:role/lambda_crons_role',
    'description': 'Lambda function: {}',
    'handler': 'lambda_function.lambda_handler',
    'enabled': True,
}

VALID_TRIGGER_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


class Deploy():
    """Command line tool to deploy cron style lambda functions to AWS."""

    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self._setup_parser()
        self.args = self.parser.parse_args()

        self.init_aws()

        self.subdir = self.args.subdir.strip('/')
        self.nonce = str(int(time.time()))

        self.root = os.environ.get('ROOTDIR', os.getcwd())
        self.dirpath = os.path.join(self.root, self.subdir)

        self.load_function_config()
        self.event_rule_name = self.schedule_expression_to_event_rule_name(
            self.config['schedule_expression']
        )

    def _setup_parser(self):
        self.parser.add_argument("subdir", help="subdirectory of lambda function")
        self.parser.add_argument("--profile", help="AWS profile to use")
        self.parser.add_argument("--region", help="AWS region to use")

    def init_aws(self):
        self.aws_profile = self.args.profile
        self.aws_region = self.args.region or DEFAULT_AWS_REGION
        session = (boto3.session.Session(profile_name=self.aws_profile)
                   if self.aws_profile else boto3.session.Session())
        self.lambda_client = session.client('lambda', region_name=self.aws_region)
        self.s3_client = session.client('s3', region_name=self.aws_region)
        self.events_client = session.client('events', region_name=self.aws_region)

    def upload_package(self):
        local_file_path = LOCAL_PATH_FORMAT.format(
            function_name=self.function_name
        )
        key = KEY_FORMAT.format(
            function_name=self.function_name,
            nonce=self.nonce,
        )
        print("Uploading {} to {}".format(
            local_file_path,
            '{}:::{}'.format(S3_BUCKET, key)
        ))
        self.s3_client.upload_file(local_file_path, S3_BUCKET, key)
        print("Upload complete!")

    def load_function_config(self):
        with open(os.path.join(self.dirpath, 'config.yml'), 'r') as f:
            self.config = yaml.safe_load(f)

        self.validate_config()

        self.function_name = self.subdir
        self.config['enabled'] = self.config.get('enabled', DEFAULT_CONFIG['enabled'])
        self.config['runtime'] = self.config.get('runtime', DEFAULT_CONFIG['runtime'])
        self.config['role'] = self.config.get('role', DEFAULT_CONFIG['role'])
        self.config['description'] = self.config.get(
            'description', DEFAULT_CONFIG['description'].format(self.subdir)
        )
        if not self.config['enabled']:
            self.config['description'] = 'DISABLED - {}'.format(self.config['description'])
        self.config['handler'] = self.config.get('handler', DEFAULT_CONFIG['handler'])
        self.config['s3_bucket'] = self.config['code']['s3_bucket']
        self.config['s3_key'] = self.config['code']['s3_key_format'].format(nonce=self.nonce)

    def validate_config(self):
        if 'code' not in self.config:
            raise ValueError('`code` must be defined')
        if not self.config.get('schedule_expression', None):
            raise ValueError('`schedule_expression` must be defined and not empty')
        if not self.config['schedule_expression'].startswith(('cron', 'rate')):
            raise ValueError('`schedule_expression` must be for cron or rate')
        if '{nonce}' not in self.config['code']['s3_key_format']:
            raise ValueError('{nonce} must be present in s3_key_format')

    def schedule_expression_to_event_rule_name(self, expression):
        split_expression = expression.replace('*', 'x').replace('?', 'q').strip(')').split('(')
        expression_type = split_expression[0]
        expression_statement = '_'.join(split_expression[1].replace(',', ' ').split(' '))
        return '{}-{}'.format(
            expression_type,
            expression_statement
        )

    def get_existing_triggering_event_rules(self, lambda_arn):
        response = self.events_client.list_rule_names_by_target(TargetArn=lambda_arn)
        return response['RuleNames']

    def event_rule_arn(self):
        try:
            response = self.events_client.describe_rule(Name=self.event_rule_name)
        except ClientError as exception:
            if exception.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            raise exception

        return response['Arn']

    def remove_target_from_event_triggers(self, function_arn, event_names):
        for event_name in event_names:
            response = self.events_client.list_targets_by_rule(Rule=event_name)
            target_id = next(target for target in response['Targets']
                             if target['Arn'] == function_arn)['Id']
            self.events_client.remove_targets(
                Rule=event_name,
                Ids=[target_id]
            )

    def create_event_trigger(self):
        response = self.events_client.put_rule(
            Name=self.event_rule_name,
            ScheduleExpression=self.config['schedule_expression']
        )
        return response['RuleArn']

    def add_trigger_to_event(self, rule_arn, function_arn):
        self.events_client.put_targets(
            Rule=self.event_rule_name,
            Targets=[{
                'Id': self.function_name,
                'Arn': function_arn
            }]
        )
        self.lambda_client.add_permission(
            FunctionName=self.function_name,
            StatementId=self.event_rule_name,
            Action='lambda:InvokeFunction',
            Principal='events.amazonaws.com',
            SourceArn=rule_arn,
        )

    def lambda_function_exists(self):
        try:
            self.lambda_client.get_function(FunctionName=self.function_name)
        except ClientError as exception:
            if exception.response['Error']['Code'] == 'ResourceNotFoundException':
                return False
            raise exception
        return True

    def create_lambda_function(self):
        response = self.lambda_client.create_function(
            FunctionName=self.function_name,
            Runtime=self.config['runtime'],
            Description=self.config['description'],
            Role=self.config['role'],
            Handler=self.config['handler'],
            Code={
                'S3Bucket': self.config['s3_bucket'],
                'S3Key': self.config['s3_key'],
            },
        )
        return response['FunctionArn']

    def delete_lambda_function(self):
        self.lambda_client.delete_function(
            FunctionName=self.function_name
        )

    def update_lambda_function(self):
        self.lambda_client.update_function_configuration(
            FunctionName=self.function_name,
            Runtime=self.config['runtime'],
            Role=self.config['role'],
            Handler=self.config['handler'],
        )
        response = self.lambda_client.update_function_code(
            FunctionName=self.function_name,
            S3Bucket=self.config['s3_bucket'],
            S3Key=self.config['s3_key'],
            Publish=True,
        )
        return response['FunctionArn']

    def make(self, *args, **kwargs):
        envs = ['{}={}'.format(key.upper(), value) for key, value in kwargs.items()]
        cmd = envs + ['make'] + list(args)
        subprocess.call(' '.join(cmd), shell=True)

    def _run(self):
        self.make('clean')
        self.make('_package', lambda_function=self.subdir)

        # Uploads the lambda function package to S3
        self.upload_package()

        # Delete the old lambda function instead of updating in order to not have to deal with
        # versioning.
        if self.lambda_function_exists():
            print("Lambda function exists - deleting")
            self.delete_lambda_function()

        print("Creating lambda function")
        function_arn = self.create_lambda_function()

        # We need to check for triggers even though we deleted the last lambda function before
        # the resulting ARN of the new one will be the same, so the old trigger will still work.
        print("Checking for existing triggers")
        existing_trigger_names = self.get_existing_triggering_event_rules(function_arn)
        if existing_trigger_names:
            print("Found {}, removing!".format(len(existing_trigger_names)))
            self.remove_target_from_event_triggers(function_arn, existing_trigger_names)

        rule_arn = self.event_rule_arn()
        if not rule_arn:
            print("Event does not exist - creating")
            rule_arn = self.create_event_trigger()

        if self.config['enabled']:
            print("Updating event with trigger")
            self.add_trigger_to_event(rule_arn, function_arn)
        else:
            print("Function not enabled, not adding trigger")


    def run(self):
        self._run()
        print("Done!")
        print("")
        print("Invoke with:")
        print("   python invoke.py {function_name} {profile}".format(
            function_name=self.function_name,
            profile=('--profile={}'.format(self.aws_profile)
                     if self.aws_profile else '')
            ))
        print('')

if __name__ == '__main__':
    Deploy().run()
