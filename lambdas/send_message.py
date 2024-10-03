import os
import boto3
import json

client = boto3.client('apigatewaymangagementapi', endpoint_url= os.environ['ENDPOINT_URL'])

ddb = boto3.resource('dynamodb')
table = ddb.Table(os.environ['TABLE_NAME'])

def handler(event, context):
    #takes an amount of connection IDS
    connectionIds = []
    try:
        response = table.scan()
        itr = response['Items']
        print(itr)
        for item in itr:
            connectionIds.append(item['connectionId'])
            print(connectionIds)
    except:
        pass

    for connectionId in connectionIds:
        #Sends message to all connected IDs
        response_message = f"lambda response: {event}"
        client.post_to_connection(Data = json.dumps(response_message), ConnectionId=connectionId)

        return {"statusCode": 200}

if __name__ == '__main__':
    handler(event = {}, context = None)