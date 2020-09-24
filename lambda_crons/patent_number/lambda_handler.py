from datetime import datetime, timezone
from dateutil import parser as date_parser
import json
import os

import requests

from base.lambda_handler_base import LambdaHandler

SEARCH_URL = 'https://ped.uspto.gov/api/queries'
PAYLOAD_FILE = 'payload.json'

HAPTIC_APPLICATION_NUMBER = '15655488'
PEDIGREE_APPLICATION_NUMBER = '16948311'

TRANSACTIONS_LIMIT = 5


def get_days_since_update(last_update_timestamp):
    # Assumes timestamp is UTC
    last_updated_dt = date_parser.parse(last_update_timestamp)
    now_dt = datetime.now(timezone.utc)
    delta = now_dt - last_updated_dt
    return delta.days


class PatentNumberLambdaHandler(LambdaHandler):
    sns_subject_template = "Patent Number Update"
    patent_application_format = 'patent_application-{}'

    state_keys = {'app_status', 'last_updated', 'patent_number', 'available'}

    def __init__(self):
        super(PatentNumberLambdaHandler, self).__init__()
        self.application_number = None

    @property
    def ddb_state_id(self):
        return self.patent_application_format.format(self.application_number)

    def _build_result_from_doc(self, doc):
        # "Recent" in this context is within the last day, since this should run every day
        updated_recently = get_days_since_update(doc['lastUpdatedTimestamp']) < 1

        patent_number = doc.get('patentNumber', '')
        available = bool(patent_number)

        result = {
            'application_number': doc['applIdStr'],
            'recent_transactions': doc['transactions'][:TRANSACTIONS_LIMIT],
            'patent_number': patent_number,
            'patent_title': doc['patentTitle'],
            'app_status': doc['appStatus_txt'],
            'last_updated': doc['lastUpdatedTimestamp'],
            'updated_recently': updated_recently,
            'available': available,
        }
        print(result)

        return result

    def _build_empty_result(self, application_number):
        return {
            'application_number': application_number,
            'recent_transactions': [],
            'patent_number': '',
            'patent_title': '',
            'app_status': '',
            'last_updated': '',
            'updated_recently': False,
            'available': False,
        }

    def _run(self, event, context):
        base_directory = os.path.dirname(os.path.abspath(__file__))
        payload = json.load(open(os.path.join(base_directory, PAYLOAD_FILE)))

        response = requests.post(
            SEARCH_URL,
            json=payload,
        )

        data = response.json()
        docs = data['queryResults']['searchResponse']['response']['docs']
        doc = docs and docs[0]

        self.application_number = payload['searchText'].split('(')[1].split(')')[0]
        result = self._build_result_from_doc(doc) if doc else self._build_empty_result(self.application_number)

        return result


def lambda_handler(event, context):
    return PatentNumberLambdaHandler().handle(event, context)


if __name__ == '__main__':
    print('Use invoke.py please!')
    print('   python invoke.py patent_number --local')
