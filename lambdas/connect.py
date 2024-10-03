import os
import boto3

ddb = boto3.resource('dynamodb')
table = ddb.Table(os.environ['TABLE_NAME'])

def handler(event, context):

    print(event)
    # Takes connection ID and puts it into the table
    try:
        table.put_item(Item = {"ConnectionId": event["requestContext"]["connectionId"]})

    except:
        pass
    return {"statusCode": 200}