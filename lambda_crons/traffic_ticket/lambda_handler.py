import json
import os

import boto3
import requests

from base.lambda_handler_base import LambdaHandler

TOKEN_URL = "http://portal.scscourt.org/api/traffic/token"
SEARCH_URL = "http://portal.scscourt.org/api/traffic/search"

SSM_DL_NUMBER = 'driver_license_number'
SSM_BIRTHDATE = 'birthdate'


class TrafficTicketLambdaHandler(LambdaHandler):
    sns_subject_template = "Ticket Update"
    sns_subject_error = "Ticket Update Error!"

    ddb_state_id = "traffic_ticket_status"

    state_keys = {'available'}

    def _run(self, event, context):
        response = requests.get(TOKEN_URL)

        dl_number = self.get_parameter(SSM_DL_NUMBER)
        birthdate = self.get_parameter(SSM_BIRTHDATE)

        token = response.json()['token']
        headers = {'Portal-Token': token}
        payload = {
            'type': 'dl',
            'userMessage': '',
            'value': dl_number,
            'dateOfBirth': birthdate,
        }
        response = requests.post(SEARCH_URL, headers=headers, json=payload)
        data = response.json()

        if 'data' not in data:
            raise ValueError('received data in unexpected format: \n{}'.format(json.dumps(data, indent=4)))

        return {
            'available': bool(data['data']),
            'response_string': json.dumps(data, indent=4),
        }


def lambda_handler(event, context):
    return TrafficTicketLambdaHandler().handle(event, context)


if __name__ == '__main__':
    print('Use invoke.py please!')
    print('   python invoke.py traffic_ticket --local')
