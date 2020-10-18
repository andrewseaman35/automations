import os
import traceback

import boto3
import jinja2


class LambdaHandler():
    sns_arn = 'arn:aws:sns:us-east-1:560983357304:lambda_crons'
    sns_subject_template = "Lambda Cron Update"
    sns_subject_error = "Lambda Cron Error!"
    sns_template_filename = 'sns_template.jinja2'

    def _parse_event(self, event):
        self.is_local = event.get('local', False)
        self.local_dir = event.get('local_dir', None)
        self.allow_aws = event.get('allow_aws', False) if self.is_local else True
        self.take_input = event.get('take_input', False) if self.is_local else False
        self.aws_profile = event.get('aws_profile', None) if self.is_local and self.allow_aws else None

    def _init_aws(self):
        session = (boto3.session.Session(profile_name=self.aws_profile)
           if self.aws_profile else boto3.session.Session())
        self.ddb_client = session.client('dynamodb')
        self.sns_client = session.client('sns')
        self.ssm_client = session.client('ssm')

    def _before_run(self, event):
        self._parse_event(event)
        self._init_aws()
        self.template_env = self.init_template_env()
        self.sns_template = self.template_env.get_template(self.sns_template_filename)

    def init_template_env(self):
        template_search_path = '{}/'.format(self.local_dir) if self.is_local else './'
        template_loader = jinja2.FileSystemLoader(searchpath=template_search_path)
        template_env = jinja2.Environment(loader=template_loader)
        return template_env

    def _run(self, event, context):
        raise NotImplementedError()

    def _after_run(self, result):
        content = self.build_content_from_result(result)
        if content:
            self.send_sns(self.sns_subject_template, content)

    def handle(self, event, context):
        try:
            self._before_run(event)
            result = self._run(event, context)
            self._after_run(result)
        except Exception as e:
            print('Uh oh, error!')
            self._handle_error(e)
            traceback.print_exc()

    def _handle_error(self, e):
        content = 'Hello! Looks like your function failed...\n'
        content += 'Here\'s the exception: \n'
        content += '{}'.format(str(e))
        self.send_sns(
            subject=self.sns_subject_error,
            content=content,
        )

    def build_content_from_result(self, result):
        return self.sns_template.render(**result)

    def get_parameter(self, name):
        if self.allow_aws:
            response = self.ssm_client.get_parameter(Name=name)
            value = response['Parameter']['Value']
        else:
            if  self.is_local and self.take_input:
                value = input("Value required from Parameter Store, {}: ".format(name))
            else:
                print("Value required from Parameter Store, checking ENV")
                value = os.environ.get(name)
                if not value:
                    raise ValueError("{} required, either add `--take-input` flag or add to ENV".format(name))
        return value

    def send_sns(self, subject, content):
        print("\n++++++++++++++\n")
        print("SNS Content{}:".format("" if self.allow_aws else " (not sent)"))
        print("\n=====\n")
        print("Subject: {}".format(subject))
        print("\n---\n")
        print(content)
        print("\n++++++++++++++\n")
        if self.allow_aws:
            self.sns_client.publish(
                TopicArn=self.sns_arn,
                Subject=subject,
                Message=content,
            )
