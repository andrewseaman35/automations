from collections import defaultdict
import json

import boto3


# If any sensor crosses this threshold, send the associated notification
SNS_EMAIL_ANY_THRESHOLD = 30

# If the average of the sensors crosses this threshold on any single record,
# send a notification
SNS_EMAIL_AVG_THRESHOLD = 15

SNS_EMAIL_TOPIC_ARN = 'arn:aws:sns:us-east-1:560983357304:SaltLevelEmail'
sns_client = boto3.client('sns')


def parse_item(item):
    """
    Convert the DynamoDB item into an easily usable dict.
    """
    sensor_ids = [key for key in item.keys() if key.startswith('sensor_')]
    return {
        'water_softener_id': item['water_softener_id']['S'],
        'timestamp': int(item['timestamp']['N']),
        'sensor_data': [
            {
                'sensor_id': sensor_id,
                'value': int(item[sensor_id]['N']),
            } for sensor_id in sensor_ids
        ],
    }

def find_threshold_breakers(records_by_water_softener_id):
    max_email = []
    average_email = []
    for water_softener_id, records in records_by_water_softener_id.items():
        for record in records:
            sensor_data = record['sensor_data']
            average_sensor_value = sum([s['value'] for s in sensor_data]) / len(sensor_data)
            max_sensor = max(sensor_data, key=lambda s: s['value'])

            anything_sent = False
            if average_sensor_value >= SNS_EMAIL_AVG_THRESHOLD:
                average_email.append(record)
                anything_sent = True
            elif max_sensor['value'] >= SNS_EMAIL_ANY_THRESHOLD:
                max_email.append(record)
                anything_sent = True

            if anything_sent:
                break
    return {
        'max_email': max_email,
        'average_email': average_email,
    }


def build_and_send_email(max_records, average_records):
    subject = 'Salt Level Threshold Crossed'
    max_crossed = bool(max_records)
    average_crossed = bool(average_records)

    if max_crossed and average_crossed:
        opener = "Both salt level thresholds have been crossed."
    else:
        opener = "The {} salt level threshold has been crossed.".format(
            "max" if max_crossed else "average"
        )

    body = (
        "Hello!\n" +
        opener +
        "\n" +
        "Records: " +
        "\n"
    )

    if max_crossed:
        body += "\n== Max Threshold Crossed ==\n"
    for record in max_records:
        sensor_strings = ["{sensor_id}: {value}".format(**sensor) for sensor in record['sensor_data']]
        body += (
            "Water softener id: {}\n".format(record['water_softener_id']) +
            '\n\t'.join(sensor_strings) +
            "\n"
        )

    if average_crossed:
        body += "\n== Average Threshold Crossed ==\n"
    for record in average_records:
        sensor_strings = ["{sensor_id}: {value}".format(**sensor) for sensor in record['sensor_data']]
        body += (
            "Water softener id: {}\n".format(record['water_softener_id']) +
            '\n\t'.join(sensor_strings) +
            "\n"
        )

    sns_client.publish(
        TopicArn=SNS_EMAIL_TOPIC_ARN,
        Message=body,
        Subject=subject,
    )


def lambda_handler(event, context):
    # Sort items so the most recent one is first
    sorted_insert_records = sorted(
        [rec for rec in event['Records'] if rec['eventName'] == 'INSERT'],
        key=lambda record: int(record['dynamodb']['NewImage']['timestamp']['N']),
        reverse=True,
    )
    print("== Records ==")
    print(json.dumps(sorted_insert_records, indent=2))
    print("== End Records ==")

    records_by_water_softener_id = defaultdict(list)
    for record in sorted_insert_records:
        item = record['dynamodb']['NewImage']
        water_softener_id = item['water_softener_id']['S']

        records_by_water_softener_id[water_softener_id].append(parse_item(item))

    threshold_breakers = find_threshold_breakers(records_by_water_softener_id);
    max_email = threshold_breakers['max_email']
    average_email = threshold_breakers['average_email']

    if max_email + average_email:
        email_body = build_and_send_email(max_email, average_email)

    print("Complete")
    if max_email + average_email:
        print("   Threshold crossed: email sent")
    else:
        print("   Threshold not crossed")
