import argparse
import json
import importlib
import os

import boto3


class Invoke():
    def __init__(self):
        self.parser = argparse.ArgumentParser()
        self._setup_parser()
        self.args = self.parser.parse_args()
        self.allow_aws = self.args.allow_aws
        self.take_input = self.args.take_input
        self.stub = self.args.stub

        if not self.args.local or self.allow_aws:
            self.init_aws()

        self.event = {}
        if self.stub:
            self.event = self._read_stub(self.stub)
        print(self.event)

        self.lambda_function_name = self.args.lambda_function_name.strip('/')

    def _read_stub(self, stub):
        stubfile_dir = os.path.join(os.path.dirname(__file__), "test_events")
        return json.load(open(os.path.join(stubfile_dir, stub)))

    def init_aws(self):
        self.aws_profile = self.args.profile
        session = (boto3.session.Session(profile_name=self.aws_profile)
                   if self.aws_profile else boto3.session.Session())
        self.lambda_client = session.client('lambda', region_name='us-east-1')

    def _setup_parser(self):
        self.parser.add_argument("lambda_function_name", help="subdirectory of lambda function")
        self.parser.add_argument("--local", help="add if running locally, disables SNS and DDB calls", action='store_true')
        self.parser.add_argument("--allow-aws", help="if running locally, enables SNS and DDB calls", action='store_true')
        self.parser.add_argument("--take-input", help="if running locally, allows for user input values in place of parameter store", action='store_true')
        self.parser.add_argument("--stub", help="use the given stub file as the event")
        self.parser.add_argument("--profile", help="AWS profile to use")

    def _run(self):
        response = self.lambda_client.invoke(
            FunctionName=self.lambda_function_name,
        )
        print(response)

    def run(self):
        if not self.args.local:
            self._run()
        else:
            # Is this too hacky? :/
            handler = importlib.import_module("{}.lambda_handler".format(self.lambda_function_name))
            self.event.update({
                'local': True,
                'allow_aws': self.allow_aws,
                'local_dir': self.lambda_function_name,
                'take_input': self.take_input,
                'aws_profile': self.aws_profile,
            })
            handler.lambda_handler(self.event, None)



if __name__ == '__main__':
    Invoke().run()
