import json
import boto3
import os

sns = boto3.client('sns')
TOPIC_ARN = os.environ.get('TOPIC_ARN')

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))
    
    for record in event.get('Records', []):
        if record['eventName'] in ['INSERT', 'MODIFY']:
            new_image = record['dynamodb']['NewImage']
            
            store = new_image.get('Store', {}).get('S', 'Unknown')
            item = new_image.get('Item', {}).get('S', 'Unknown')
            count_str = new_image.get('Count', {}).get('N', '0')
            
            try:
                count = int(count_str)
            except ValueError:
                count = 0
            
            if count == 0:
                message = f"ALERT: Stock is 0 for {item} in {store}!"
                print(message)
                
                if TOPIC_ARN:
                    try:
                        sns.publish(
                            TopicArn=TOPIC_ARN,
                            Subject="Low Stock Alert",
                            Message=message
                        )
                        print("SNS notification sent.")
                    except Exception as e:
                        print(f"Error sending SNS: {e}")
                else:
                    print("TOPIC_ARN not configured.")
            
    return {
        'statusCode': 200,
        'body': json.dumps('Processed DynamoDB Stream')
    }
