import json
import os

import requests

from base.lambda_handler_base import LambdaHandler

SEARCH_URL = 'https://ped.uspto.gov/api/queries'
PAYLOAD_FILE = 'payload.json'
APPLICATION_NUMBER = 'US15655488'


CONTENT_TEMPLATE = '''
Patent Title: {patent_title}
Application Number: {application_number}
Last Updated: {last_updated}

Current Status: {app_status}

Recent Transactions:
{transactions}
'''


def _transaction_text_from_transactions(transactions, limit=5):
    transaction_text = ''
    for transaction in transactions[:limit]:
        transaction_text += '{recordDate}: {description}\n'.format(**transaction)
    return transaction_text


class PatentNumberLambdaHandler(LambdaHandler):
    sns_subject_template = "Patent Number Update"

    ddb_state_id = 'patent_number'

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

        transactions = doc['transactions']
        patent_number = doc['patentNumber']
        patent_title = doc['patentTitle']
        app_status = doc['appStatus_txt']
        last_updated = doc['lastUpdatedTimestamp']

        if patent_number:
            content = "Wowee! It looks like you have a patent number!\n"
            content += "  Check it out: {}\n".format(patent_number)
        else:
            content = "It doesn't look like you have a patent number just yet...\n"

        content += CONTENT_TEMPLATE.format(
            patent_title=patent_title,
            application_number=APPLICATION_NUMBER,
            last_updated=last_updated,
            app_status=app_status,
            transactions=_transaction_text_from_transactions(transactions)
        )

        cls.put_state({
            'app_status': {'S': app_status},
            'last_updated': {'S': last_updated},
            'patent_number': {'S': patent_number if patent_number else 'none'},
            'available': {'BOOL': bool(patent_number)}
        })

        cls.send_sns(
            subject=cls.sns_subject_template,
            content=content,
        )


def lambda_handler(event, context):
    return PatentNumberLambdaHandler.handle(event, context)

if __name__ == '__main__':
    print('Use invoke.py please!')
    print('   python invoke.py patent_number --local')
