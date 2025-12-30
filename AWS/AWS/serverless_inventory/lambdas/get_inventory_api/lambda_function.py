import json
import boto3
import os
import urllib.parse
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME', 'Inventory')
table = dynamodb.Table(TABLE_NAME)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*"
        },
        "body": json.dumps(body, cls=DecimalEncoder)
    }

def lambda_handler(event, context):
    print("Event:", json.dumps(event))
    
    try:
        # API Gateway HTTP API payload format v2.0
        path_parameters = event.get('pathParameters') or {}
        store = path_parameters.get('store')
        
        items = []
        
        if store:
            # Query by Store (Partition Key)
            store = urllib.parse.unquote(store)
            response = table.query(
                KeyConditionExpression=Key('Store').eq(store)
            )
            items = response.get('Items', [])
        else:
            # Scan all
            response = table.scan()
            items = response.get('Items', [])
            
            # Handle pagination if needed
            while 'LastEvaluatedKey' in response:
                response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
                items.extend(response.get('Items', []))

        return _resp(200, items)

    except Exception as e:
        print(e)
        return _resp(500, {"error": str(e)})
