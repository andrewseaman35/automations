import json
import os

import requests

from base.lambda_handler_base import LambdaHandler

SEARCH_URL = 'https://ped.uspto.gov/api/queries'
PAYLOAD_FILE = 'payload.json'
APPLICATION_NUMBER = 'US15655488'

TRANSACTIONS_LIMIT = 5


class PatentNumberLambdaHandler(LambdaHandler):
    sns_subject_template = "Patent Number Update"
    ddb_state_id = 'patent_number'

    state_keys = {'app_status', 'last_updated', 'patent_number', 'available'}

    @classmethod
    def _run(cls, event, context):
        base_directory = os.path.dirname(os.path.abspath(__file__))
        payload = json.load(open(os.path.join(base_directory, PAYLOAD_FILE)))

        response = requests.post(
            SEARCH_URL,
            json=payload,
        )

        data = response.json()

        number_found = data['queryResults']['searchResponse']['response']['numFound']
        if number_found != 1:
            content = "Whoa, there isn\'t exactly one record. There are {}!\n\n".format(number_found)
            content += "You should just look at all the data...\n\n"
            content += json.dumps(data, indent=4)
            return

        doc = data['queryResults']['searchResponse']['response']['docs'][0]

        result = {
            'application_number': doc['applIdStr'],
            'recent_transactions': doc['transactions'][:TRANSACTIONS_LIMIT],
            'patent_number': doc['patentNumber'],
            'patent_title': doc['patentTitle'],
            'app_status': doc['appStatus_txt'],
            'last_updated': doc['lastUpdatedTimestamp'],
            'available': bool(doc['patentNumber']),
        }

        return result


def lambda_handler(event, context):
    return PatentNumberLambdaHandler.handle(event, context)

if __name__ == '__main__':
    print('Use invoke.py please!')
    print('   python invoke.py patent_number --local')
