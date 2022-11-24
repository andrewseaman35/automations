from base.lambda_handler_base import LambdaHandler


CREATION_EVENT_NAME = "ObjectCreated:Put"

ACTION_CREATE = "CREATE"
ACTION_DELETE = "DELETE"



class MAMEHighScoreLambdaHandler(LambdaHandler):
    sns_subject_template = "MAME High Score Update"

    def build_content_from_result(self, result):
        context = {
            "filenames": result["changes"]
        }
        return self.sns_template.render(**context)

    def _run(self, event, context):
        records = event["Records"]

        changes = []
        for record in records:
            if record["eventName"] != CREATION_EVENT_NAME:
                # Skip deletion events. We shouldn't be deleting anyways..
                continue

            name = record["s3"]["object"]["key"]
            changes.append(name.split('hi/')[1])

        print(changes)
        return {
            "changes": changes
        }


def lambda_handler(event, context):
    return MAMEHighScoreLambdaHandler().handle(event, context)


if __name__ == '__main__':
    print('Use invoke.py please!')
    print('   python invoke.py salt_level_entry_checker --local')
