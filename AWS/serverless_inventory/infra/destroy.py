import boto3
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deploy_state.json')

if not os.path.exists(STATE_FILE):
    logger.warning("No state file found. Nothing to teardown.")
    exit()

with open(STATE_FILE, 'r') as f:
    state = json.load(f)

s3 = boto3.resource('s3')
dynamodb = boto3.client('dynamodb')
iam = boto3.client('iam')
lambda_client = boto3.client('lambda')
apigateway = boto3.client('apigatewayv2')
sns = boto3.client('sns')

def delete_bucket(bucket_name):
    logger.info(f"Deleting bucket {bucket_name}...")
    try:
        bucket = s3.Bucket(bucket_name)
        bucket.objects.all().delete()
        bucket.object_versions.all().delete()
        bucket.delete()
    except Exception as e:
        logger.error(f"Error deleting bucket {bucket_name}: {e}")

def delete_table(table_name):
    logger.info(f"Deleting table {table_name}...")
    try:
        dynamodb.delete_table(TableName=table_name)
        waiter = dynamodb.get_waiter('table_not_exists')
        waiter.wait(TableName=table_name)
    except dynamodb.exceptions.ResourceNotFoundException:
        pass
    except Exception as e:
        logger.error(f"Error deleting table {table_name}: {e}")

def delete_lambda(function_name):
    logger.info(f"Deleting Lambda {function_name}...")
    try:
        lambda_client.delete_function(FunctionName=function_name)
    except lambda_client.exceptions.ResourceNotFoundException:
        pass
    except Exception as e:
        logger.error(f"Error deleting lambda {function_name}: {e}")

def delete_role(role_name):
    logger.info(f"Deleting role {role_name}...")
    try:
        policies = iam.list_attached_role_policies(RoleName=role_name)['AttachedPolicies']
        for p in policies:
            iam.detach_role_policy(RoleName=role_name, PolicyArn=p['PolicyArn'])
        
        inline_policies = iam.list_role_policies(RoleName=role_name)['PolicyNames']
        for p_name in inline_policies:
            iam.delete_role_policy(RoleName=role_name, PolicyName=p_name)

        iam.delete_role(RoleName=role_name)
    except iam.exceptions.NoSuchEntityException:
        pass
    except Exception as e:
        logger.error(f"Error deleting role {role_name}: {e}")

def delete_api(api_name):
    logger.info(f"Deleting API {api_name}...")
    try:
        apis = apigateway.get_apis()
        for item in apis.get('Items', []):
            if item['Name'] == api_name:
                apigateway.delete_api(ApiId=item['ApiId'])
                break
    except Exception as e:
        logger.error(f"Error deleting API {api_name}: {e}")

def delete_sns_topic(topic_arn):
    if not topic_arn: return
    logger.info(f"Deleting SNS topic {topic_arn}...")
    try:
        sns.delete_topic(TopicArn=topic_arn)
    except Exception as e:
        logger.error(f"Error deleting SNS topic: {e}")

def main():
    if 'BUCKET_UPLOADS' in state: delete_bucket(state['BUCKET_UPLOADS'])
    if 'BUCKET_WEB' in state: delete_bucket(state['BUCKET_WEB'])
    if 'TABLE_NAME' in state: delete_table(state['TABLE_NAME'])
    if 'LAMBDA_LOAD_NAME' in state: delete_lambda(state['LAMBDA_LOAD_NAME'])
    if 'LAMBDA_GET_NAME' in state: delete_lambda(state['LAMBDA_GET_NAME'])
    if 'LAMBDA_NOTIFY_NAME' in state: delete_lambda(state['LAMBDA_NOTIFY_NAME'])
    if 'API_NAME' in state: delete_api(state['API_NAME'])
    if 'TOPIC_ARN' in state: delete_sns_topic(state['TOPIC_ARN'])

    if 'ROLES' in state:
        for role in state['ROLES']:
            delete_role(role)
        
    logger.info("Teardown complete.")
    try:
        os.remove(STATE_FILE)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for f in os.listdir(base_dir):
            if f.endswith('.zip'):
                os.remove(os.path.join(base_dir, f))
    except Exception as e:
        logger.error(f"Error cleaning up local files: {e}")

if __name__ == '__main__':
    main()
