import boto3
import json

# Verificar DynamoDB
ddb = boto3.client('dynamodb')
resp = ddb.scan(TableName='Inventory')
items = resp.get('Items', [])
print(f'Items en DynamoDB: {len(items)}')
for item in items:
    store = item['Store']['S']
    itemname = item['Item']['S']
    count = item['Count']['N']
    print(f'  - {store}: {itemname} (qty: {count})')

# Verificar API
print('\nProbando API:')
import urllib.request
try:
    url = 'https://ghqub7cfdb.execute-api.us-east-1.amazonaws.com/items'
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode('utf-8'))
        print(f'API respondio: {len(data)} items')
        for item in data[:3]:
            print(f"  {item}")
except Exception as e:
    print(f'Error en API: {e}')
