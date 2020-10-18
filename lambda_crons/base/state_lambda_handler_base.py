import datetime
import json

from .lambda_handler_base import LambdaHandler


STATE_TABLE = 'states'


class StateLambdaHandler(LambdaHandler):
    def _after_run(self, result):
        state = self.build_state_from_result(result)
        self.put_state(state)
        content = self.build_content_from_result(result)
        if content:
            self.send_sns(self.sns_subject_template, content)

    def build_state_from_result(self, result):
        state = {}
        for key, value in result.items():
            if key not in self.state_keys:
                continue
            if isinstance(value, str):
                _type = 'S'
                value = value or 'none'
            elif isinstance(value, bool):
                _type = 'BOOL'
            else:
                raise TypeError('unsupported type for {}: {}'.format(value, type(value)))

            state[key] = {
                _type: value
            }
        return state

    def put_state(self, item):
        item.update({
            'id': {
                'S': self.ddb_state_id,
            },
            'time_updated': {
                'S': datetime.datetime.now().isoformat(),
            }
        })
        print("\n++++++++++++++\n")
        print("New DynamoDB State{}:".format("" if self.allow_aws else " (not updated)"))
        print("\n=====\n")
        print(json.dumps(item, indent=4))
        print("\n++++++++++++++\n")
        if self.allow_aws:
            self.ddb_client.put_item(
                TableName=STATE_TABLE,
                Item=item
            )
