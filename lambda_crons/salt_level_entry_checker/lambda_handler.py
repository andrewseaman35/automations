from datetime import datetime, date
from dateutil import parser as date_parser
import json
import os

import requests

from base.lambda_handler_base import LambdaHandler

PROD_TABLE_NAME = 'salt_level'
DEV_TABLE_NAME = 'salt_level_local'

WATER_SOFTENER_ID = 'softener_one'


class SaltLevelEntryCheckerLambdaHandler(LambdaHandler):
    sns_subject_template = "Salt Level Entry not found!"

    @property
    def table_name(self):
        return DEV_TABLE_NAME if self.is_local else PROD_TABLE_NAME

    def build_content_from_result(self, result):
        if result['days_since_last_entry'] == 0:
            print("New salt level entry found within the past day, nothing to do!")
            return None

        context = {
            'formatted_today_date': date.today().strftime('%B %d, %Y'),
            'days_since_last_entry': result['days_since_last_entry']
        }
        return self.sns_template.render(**context)

    def most_recent_entry(self, water_softener_id):
        result = self.ddb_client.query(
            TableName=self.table_name,
            Select='SPECIFIC_ATTRIBUTES',
            ProjectionExpression='#ts',
            ConsistentRead=True,
            ScanIndexForward=False,
            Limit=1,
            KeyConditionExpression='water_softener_id = :wsid',
            ExpressionAttributeValues={
                ':wsid': {
                    'S': water_softener_id,
                },
            },
            ExpressionAttributeNames={
                '#ts': 'timestamp',
            },
        )

        items = result.get('Items', None)
        if items:
            return items[0]
        return None

    def _run(self, event, context):
        entry = self.most_recent_entry(WATER_SOFTENER_ID)
        print('Found: {}'.format(entry))

        if not entry:
            return {
                'days_since_last_entry': -1
            }

        entry_timestamp = datetime.fromtimestamp(int(entry['timestamp']['N']))
        time_since = datetime.now() - entry_timestamp

        return {
            'days_since_last_entry': time_since.days
        }


def lambda_handler(event, context):
    return SaltLevelEntryCheckerLambdaHandler().handle(event, context)


if __name__ == '__main__':
    print('Use invoke.py please!')
    print('   python invoke.py salt_level_entry_checker --local')
