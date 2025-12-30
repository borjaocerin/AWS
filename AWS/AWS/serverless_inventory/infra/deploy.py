import boto3
import json
import os
import time
import zipfile
import random
import string
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'deploy_state.json')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load or generate suffix
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
        SUFFIX = state.get('SUFFIX', ''.join(random.choices(string.ascii_lowercase + string.digits, k=6)))
else:
    SUFFIX = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    state = {}

REGION = boto3.session.Session().region_name or 'us-east-1'
sts = boto3.client('sts')
try:
    ACCOUNT_ID = sts.get_caller_identity()['Account']
except Exception:
    logger.error("Could not get AWS Account ID. Please configure AWS credentials.")
    exit(1)

# Resource Names
BUCKET_UPLOADS = f"inventory-uploads-{SUFFIX}"
BUCKET_WEB = f"inventory-web-{SUFFIX}"
TABLE_NAME = "Inventory"
TOPIC_NAME = "NoStock"
LAMBDA_LOAD_NAME = "load_inventory"
LAMBDA_GET_NAME = "get_inventory_api"
LAMBDA_NOTIFY_NAME = "notify_low_stock"
API_NAME = "InventoryAPI"

# Clients
s3 = boto3.client('s3')
dynamodb = boto3.client('dynamodb')
iam = boto3.client('iam')
lambda_client = boto3.client('lambda')
apigateway = boto3.client('apigatewayv2')
sns = boto3.client('sns')

def create_bucket(bucket_name):
    logger.info(f"Creating bucket {bucket_name}...")
    try:
        if REGION == 'us-east-1':
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': REGION}
            )
    except s3.exceptions.BucketAlreadyOwnedByYou:
        logger.info(f"Bucket {bucket_name} already exists.")
    except Exception as e:
        logger.error(f"Error creating bucket {bucket_name}: {e}")

def create_dynamodb_table():
    logger.info(f"Creating DynamoDB table {TABLE_NAME}...")
    try:
        dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {'AttributeName': 'Store', 'KeyType': 'HASH'},
                {'AttributeName': 'Item', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'Store', 'AttributeType': 'S'},
                {'AttributeName': 'Item', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST',
            StreamSpecification={
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            }
        )
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=TABLE_NAME)
        logger.info(f"Table {TABLE_NAME} created.")
    except dynamodb.exceptions.ResourceInUseException:
        logger.info(f"Table {TABLE_NAME} already exists.")
        # Ensure stream is enabled if it exists
        try:
            desc = dynamodb.describe_table(TableName=TABLE_NAME)
            if not desc['Table'].get('StreamSpecification', {}).get('StreamEnabled'):
                dynamodb.update_table(
                    TableName=TABLE_NAME,
                    StreamSpecification={
                        'StreamEnabled': True,
                        'StreamViewType': 'NEW_AND_OLD_IMAGES'
                    }
                )
                logger.info(f"Enabled streams for {TABLE_NAME}")
        except Exception as e:
            logger.error(f"Error checking/updating table stream: {e}")

def create_sns_topic():
    logger.info(f"Creating SNS topic {TOPIC_NAME}...")
    try:
        response = sns.create_topic(Name=TOPIC_NAME)
        return response['TopicArn']
    except Exception as e:
        logger.error(f"Error creating SNS topic: {e}")
        return None

def create_iam_role(role_name, policy_arns, assume_role_policy):
    logger.info(f"Creating IAM role {role_name}...")
    try:
        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy)
        )
    except iam.exceptions.EntityAlreadyExistsException:
        logger.info(f"Role {role_name} already exists.")

    for policy_arn in policy_arns:
        try:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
        except Exception as e:
            logger.error(f"Error attaching policy {policy_arn} to {role_name}: {e}")
    
    time.sleep(5) # Wait for propagation
    return f"arn:aws:iam::{ACCOUNT_ID}:role/{role_name}"

def zip_lambda(function_name):
    zip_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'{function_name}.zip')
    source_file = os.path.join(PROJECT_ROOT, 'lambdas', function_name, 'lambda_function.py')
    
    if not os.path.exists(source_file):
        logger.error(f"Source file not found: {source_file}")
        return None

    with zipfile.ZipFile(zip_path, 'w') as z:
        z.write(source_file, 'lambda_function.py')
    return zip_path

def create_lambda(function_name, role_arn, handler, zip_path, env_vars={}):
    logger.info(f"Creating Lambda {function_name}...")
    if not zip_path: return None

    with open(zip_path, 'rb') as f:
        zipped_code = f.read()

    try:
        lambda_client.create_function(
            FunctionName=function_name,
            Runtime='python3.11',
            Role=role_arn,
            Handler=handler,
            Code={'ZipFile': zipped_code},
            Timeout=30,
            Environment={'Variables': env_vars}
        )
    except lambda_client.exceptions.ResourceConflictException:
        logger.info(f"Lambda {function_name} already exists. Updating code...")
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zipped_code
        )
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={'Variables': env_vars}
        )
    
    return f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{function_name}"

def create_api_gateway(lambda_arn):
    logger.info("Creating API Gateway...")
    
    apis = apigateway.get_apis()
    api_id = None
    for item in apis.get('Items', []):
        if item['Name'] == API_NAME:
            api_id = item['ApiId']
            logger.info(f"API {API_NAME} already exists with ID {api_id}")
            break
    
    if not api_id:
        api = apigateway.create_api(
            Name=API_NAME,
            ProtocolType='HTTP',
            CorsConfiguration={
                'AllowOrigins': ['*'],
                'AllowMethods': ['GET', 'OPTIONS'],
                'AllowHeaders': ['*']
            }
        )
        api_id = api['ApiId']
    
    api_endpoint = f"https://{api_id}.execute-api.{REGION}.amazonaws.com"

    # Integration
    integrations = apigateway.get_integrations(ApiId=api_id)
    integration_id = None
    for i in integrations.get('Items', []):
        if i.get('IntegrationUri') == lambda_arn:
            integration_id = i['IntegrationId']
            break
            
    if not integration_id:
        integration = apigateway.create_integration(
            ApiId=api_id,
            IntegrationType='AWS_PROXY',
            IntegrationUri=lambda_arn,
            PayloadFormatVersion='2.0'
        )
        integration_id = integration['IntegrationId']

    # Routes
    for route_key in ['GET /items', 'GET /items/{store}']:
        try:
            apigateway.create_route(
                ApiId=api_id,
                RouteKey=route_key,
                Target=f"integrations/{integration_id}"
            )
        except apigateway.exceptions.ConflictException:
            pass

    # Create Stage
    try:
        apigateway.create_stage(
            ApiId=api_id,
            StageName='$default',
            AutoDeploy=True
        )
    except apigateway.exceptions.ConflictException:
        pass

    # Permission
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_GET_NAME,
            StatementId=f'apigateway-invoke-{api_id}',
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            SourceArn=f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*/*"
        )
    except lambda_client.exceptions.ResourceConflictException:
        pass

    return api_endpoint

def main():
    # 1. Create Buckets
    create_bucket(BUCKET_UPLOADS)
    create_bucket(BUCKET_WEB)

    # 2. Create DynamoDB
    create_dynamodb_table()
    
    # 3. Create SNS
    topic_arn = create_sns_topic()

    # 4. Create IAM Roles
    # Use AWS Academy LabRole (preexisting role with necessary permissions)
    logger.info("Using AWS Academy LabRole for Lambda functions...")
    
    # Get account ID to construct LabRole ARN
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    lab_role_arn = f"arn:aws:iam::{account_id}:role/LabRole"
    
    load_role_arn = lab_role_arn
    get_role_arn = lab_role_arn
    notify_role_arn = lab_role_arn
    
    logger.info(f"Using role: {lab_role_arn}")

    # 5. Create Lambdas
    load_zip = zip_lambda(LAMBDA_LOAD_NAME)
    get_zip = zip_lambda(LAMBDA_GET_NAME)
    notify_zip = zip_lambda(LAMBDA_NOTIFY_NAME)

    create_lambda(LAMBDA_LOAD_NAME, load_role_arn, 'lambda_function.lambda_handler', load_zip, {'TABLE_NAME': TABLE_NAME})
    create_lambda(LAMBDA_GET_NAME, get_role_arn, 'lambda_function.lambda_handler', get_zip, {'TABLE_NAME': TABLE_NAME})
    create_lambda(LAMBDA_NOTIFY_NAME, notify_role_arn, 'lambda_function.lambda_handler', notify_zip, {'TOPIC_ARN': topic_arn})

    # 6. S3 Trigger for Load Lambda
    logger.info("Configuring S3 notification...")
    try:
        lambda_client.add_permission(
            FunctionName=LAMBDA_LOAD_NAME,
            StatementId='s3-invoke',
            Action='lambda:InvokeFunction',
            Principal='s3.amazonaws.com',
            SourceArn=f"arn:aws:s3:::{BUCKET_UPLOADS}"
        )
    except lambda_client.exceptions.ResourceConflictException:
        pass

    s3.put_bucket_notification_configuration(
        Bucket=BUCKET_UPLOADS,
        NotificationConfiguration={
            'LambdaFunctionConfigurations': [{
                'LambdaFunctionArn': f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{LAMBDA_LOAD_NAME}",
                'Events': ['s3:ObjectCreated:*'],
                'Filter': {'Key': {'FilterRules': [{'Name': 'suffix', 'Value': '.csv'}]}}
            }]
        }
    )
    
    # 7. DynamoDB Stream Trigger for Notify Lambda
    logger.info("Configuring DynamoDB Stream trigger...")
    try:
        table_desc = dynamodb.describe_table(TableName=TABLE_NAME)
        stream_arn = table_desc['Table']['LatestStreamArn']
        
        # Check if mapping exists
        mappings = lambda_client.list_event_source_mappings(FunctionName=LAMBDA_NOTIFY_NAME)
        mapping_exists = False
        for m in mappings['EventSourceMappings']:
            if m['EventSourceArn'] == stream_arn:
                mapping_exists = True
                break
        
        if not mapping_exists:
            lambda_client.create_event_source_mapping(
                EventSourceArn=stream_arn,
                FunctionName=LAMBDA_NOTIFY_NAME,
                StartingPosition='LATEST',
                BatchSize=10
            )
    except Exception as e:
        logger.error(f"Error configuring DynamoDB stream trigger: {e}")

    # 8. API Gateway
    api_url = create_api_gateway(f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{LAMBDA_GET_NAME}")
    logger.info(f"API URL: {api_url}")

    # 9. Deploy Web
    logger.info("Deploying website...")
    index_path = os.path.join(PROJECT_ROOT, 'web', 'index.html')
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Replace placeholder
        html_content = html_content.replace("REPLACE_ME_WITH_YOUR_INVOKE_URL", api_url)
        
        # Enable static hosting
        s3.put_bucket_website(
            Bucket=BUCKET_WEB,
            WebsiteConfiguration={'IndexDocument': {'Suffix': 'index.html'}}
        )
        
        # Public access policy
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadGetObject",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{BUCKET_WEB}/*"
                }
            ]
        }
        
        # Disable Block Public Access
        s3.put_public_access_block(
            Bucket=BUCKET_WEB,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        
        s3.put_bucket_policy(Bucket=BUCKET_WEB, Policy=json.dumps(policy))
        
        s3.put_object(
            Bucket=BUCKET_WEB,
            Key='index.html',
            Body=html_content,
            ContentType='text/html'
        )

        web_url = f"http://{BUCKET_WEB}.s3-website-{REGION}.amazonaws.com"
        logger.info(f"Website URL: {web_url}")
    else:
        logger.warning(f"Web index file not found at {index_path}")
        web_url = "Not deployed"

    logger.info(f"Upload Bucket: {BUCKET_UPLOADS}")
    logger.info(f"SNS Topic ARN: {topic_arn}")

    # Save info to a file for teardown
    state.update({
        'SUFFIX': SUFFIX,
        'BUCKET_UPLOADS': BUCKET_UPLOADS,
        'BUCKET_WEB': BUCKET_WEB,
        'TABLE_NAME': TABLE_NAME,
        'TOPIC_ARN': topic_arn,
        'LAMBDA_LOAD_NAME': LAMBDA_LOAD_NAME,
        'LAMBDA_GET_NAME': LAMBDA_GET_NAME,
        'LAMBDA_NOTIFY_NAME': LAMBDA_NOTIFY_NAME,
        'API_NAME': API_NAME,
        'ROLES': ['LambdaLoadInventoryRole', 'LambdaGetInventoryRole', 'LambdaNotifyLowStockRole']
    })
    
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

if __name__ == '__main__':
    main()
