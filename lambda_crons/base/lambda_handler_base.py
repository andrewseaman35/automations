import datetime
import json
import os
import traceback

import boto3
import jinja2


STATE_TABLE = 'states'


class LambdaHandler():
    sns_arn = 'arn:aws:sns:us-east-1:560983357304:lambda_crons'
    sns_subject_template = "Lambda Cron Update"
    sns_subject_error = "Lambda Cron Error!"
    sns_template_filename = 'sns_template.jinja2'

    ddb_client = boto3.client('dynamodb')
    sns_client = boto3.client('sns')
    ssm_client = boto3.client('ssm')

    @classmethod
    def _parse_event(cls, event):
        cls.is_local = event.get('local', False)
        cls.local_dir = event.get('local_dir', None)
        cls.allow_aws = event.get('allow_aws', False) if cls.is_local else True
        cls.take_input = event.get('take_input', False) if cls.is_local else False

    @classmethod
    def _before_run(cls, event):
        cls._parse_event(event)
        cls.template_env = cls.init_template_env()
        cls.sns_template = cls.template_env.get_template(cls.sns_template_filename)

    @classmethod
    def init_template_env(cls):
        template_search_path = '{}/'.format(cls.local_dir) if cls.is_local else './'
        template_loader = jinja2.FileSystemLoader(searchpath=template_search_path)
        template_env = jinja2.Environment(loader=template_loader)
        return template_env

    @classmethod
    def _run(cls, event, context):
        raise NotImplementedError()

    @classmethod
    def _after_run(cls, result):
        state = cls.build_state_from_result(result)
        cls.put_state(state)
        content = cls.build_content_from_result(result)
        cls.send_sns(cls.sns_subject_template, content)

    @classmethod
    def handle(cls, event, context):
        try:
            cls._before_run(event)
            result = cls._run(event, context)
            cls._after_run(result)
        except Exception as e:
            print('Uh oh, error!')
            cls._handle_error(e)
            traceback.print_exc()

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
    def build_state_from_result(cls, result):
        state = {}
        for key, value in result.items():
            if key not in cls.state_keys:
                continue
            if isinstance(value, str):
                _type = 'S'
                value = value or 'none'
            elif isinstance(value, bool):
                _type = 'BOOL'
            else:
                raise TypeError('unsupported type for {}: {}'.format(value, type(value)))

            state[key] = {
                _type: value
            }
        return state

    @classmethod
    def build_content_from_result(cls, result):
        return cls.sns_template.render(**result)

    @classmethod
    def put_state(cls, item):
        item.update({
            'id': {
                'S': cls.ddb_state_id,
            },
            'time_updated': {
                'S': datetime.datetime.now().isoformat(),
            }
        })
        print("\n++++++++++++++\n")
        print("New DynamoDB State{}:".format("" if cls.allow_aws else " (not updated)"))
        print("\n=====\n")
        print(json.dumps(item, indent=4))
        print("\n++++++++++++++\n")
        if cls.allow_aws:
            cls.ddb_client.put_item(
                TableName=STATE_TABLE,
                Item=item
            )

    @classmethod
    def get_parameter(cls, name):
        if cls.allow_aws:
            response = cls.ssm_client.get_parameter(Name=name)
            value = response['Parameter']['Value']
        else:
            if  cls.is_local and cls.take_input:
                value = input("Value required from Parameter Store, {}: ".format(name))
            else:
                print("Value required from Parameter Store, checking ENV")
                value = os.environ.get(name)
                if not value:
                    raise ValueError("{} required, either add `--take-input` flag or add to ENV".format(name))
        return value

    @classmethod
    def send_sns(cls, subject, content):
        print("\n++++++++++++++\n")
        print("SNS Content{}:".format("" if cls.allow_aws else " (not sent)"))
        print("\n=====\n")
        print("Subject: {}".format(subject))
        print("\n---\n")
        print(content)
        print("\n++++++++++++++\n")
        if cls.allow_aws:
            cls.sns_client.publish(
                TopicArn=cls.sns_arn,
                Subject=subject,
                Message=content,
            )
