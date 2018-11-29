import json
import os

import boto3
import requests

from lambda_handler_base import LambdaHandler

TOKEN_URL = "http://portal.scscourt.org/api/traffic/token"
SEARCH_URL = "http://portal.scscourt.org/api/traffic/search"


class TrafficTicketLambdaHandler(LambdaHandler):
    sns_subject_template = "Ticket Update"

    @classmethod
    def _run(cls, event, context):
        response = requests.get(TOKEN_URL)

        token = response.json()['token']
        headers = {'Portal-Token': token}
        payload = {
            'type': 'dl',
            'userMessage': '',
            'value': os.environ.get('dl_number'),
            'dateOfBirth': os.environ.get('birthdate'),
        }
        response = requests.post(SEARCH_URL, headers=headers, json=payload)
        data = response.json()

        print(json.dumps(data, indent=4))

        if not data['data']:
            content = "Hello! I don't think there are any updates, but here's the data just in case!\n"
        else:
            content = "Hello! There might be something for you! Check out the data!\n"

        content += json.dumps(data, indent=4)

        cls.send_sns(
            subject=cls.sns_subject_template,
            content=content,
        )


def lambda_handler(event, context):
    return TrafficTicketLambdaHandler.handle(event, context)
