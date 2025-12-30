import json
import urllib.parse
import boto3
import csv
import io
import os

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME', 'Inventory')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))

    try:
        for record in event['Records']:
            bucket = record['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(record['s3']['object']['key'], encoding='utf-8')
            
            print(f"Processing file: {key} from bucket: {bucket}")
            
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            
            csv_reader = csv.DictReader(io.StringIO(content))
            
            with table.batch_writer() as batch:
                for row in csv_reader:
                    item_data = {}
                    for k, v in row.items():
                        if not k: continue
                        k_lower = k.strip().lower()
                        if k_lower in ['store', 'tienda']:
                            item_data['Store'] = v.strip()
                        elif k_lower in ['item', 'articulo', 'artículo']:
                            item_data['Item'] = v.strip()
                        elif k_lower in ['count', 'cantidad']:
                            try:
                                item_data['Count'] = int(v.strip())
                            except ValueError:
                                item_data['Count'] = 0
                    
                    if 'Store' in item_data and 'Item' in item_data:
                        batch.put_item(Item=item_data)
                        print(f"Added item: {item_data}")
                    else:
                        print(f"Skipping invalid row: {row}")

        return {
            'statusCode': 200,
            'body': json.dumps(f'Successfully processed file(s)')
        }
    except Exception as e:
        print(f"Error: {e}")
        raise e
