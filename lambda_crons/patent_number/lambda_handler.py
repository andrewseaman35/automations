from datetime import datetime, timezone
from dateutil import parser as date_parser
import json
import os

import requests

from base.lambda_handler_base import LambdaHandler

SEARCH_URL = 'https://ped.uspto.gov/api/queries'
PAYLOAD_FILE = 'payload.json'
APPLICATION_NUMBER = 'US15655488'

TRANSACTIONS_LIMIT = 5


def get_days_since_update(last_update_timestamp):
    # Assumes timestamp is UTC
    last_updated_dt = date_parser.parse(last_update_timestamp)
    now_dt = datetime.now(timezone.utc)
    delta = now_dt - last_updated_dt
    return delta.days


class PatentNumberLambdaHandler(LambdaHandler):
    sns_subject_template = "Patent Number Update"
    ddb_state_id = 'patent_number'

    state_keys = {'app_status', 'last_updated', 'patent_number', 'available'}

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

        return result

    def _run(self, event, context):
        base_directory = os.path.dirname(os.path.abspath(__file__))
        payload = json.load(open(os.path.join(base_directory, PAYLOAD_FILE)))

        response = requests.post(
            SEARCH_URL,
            json=payload,
        )

        data = response.json()
        doc = data['queryResults']['searchResponse']['response']['docs'][0]

        return self._build_result_from_doc(doc)


def lambda_handler(event, context):
    return PatentNumberLambdaHandler().handle(event, context)


if __name__ == '__main__':
    print('Use invoke.py please!')
    print('   python invoke.py patent_number --local')
