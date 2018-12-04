import json
import os

import requests

if os.environ.get('_HANDLER'):
    from lambda_handler_base import LambdaHandler
else:
    from base.lambda_handler_base import LambdaHandler

SEARCH_URL = 'https://ped.uspto.gov/api/queries'
PAYLOAD_FILE = 'payload.json'
APPLICATION_NUMBER = 'US15655488'


class PatentNumberLambdaHandler(LambdaHandler):
    sns_subject_template = "Patent Number Update"

    @classmethod
    def _run(cls, event, context):
        base_directory = os.path.dirname(os.path.abspath(__file__))
        payload = json.load(open(os.path.join(base_directory, PAYLOAD_FILE)))

        response = requests.post(
            SEARCH_URL,
            json=payload,
        )

        data = response.json()

        print(json.dumps(data, indent=4))



def lambda_handler(event, context):
    return PatentNumberLambdaHandler.handle(event, context)

if __name__ == '__main__':
    print('Use invoke.py please!')
    print('   python invoke.py patent_number --local')
