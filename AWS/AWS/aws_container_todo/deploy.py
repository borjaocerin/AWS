#!/usr/bin/env python3
"""
Script completo para desplegar la práctica 2 (Container TODO)
"""
import boto3
import subprocess
import time
import os

# Las credenciales se cargan automáticamente desde variables de entorno
# No necesita dotenv si ya cargaste el .env en PowerShell

# Configuración
ecr = boto3.client('ecr')
sts = boto3.client('sts')
ec2 = boto3.client('ec2')
cfn = boto3.client('cloudformation')

ACCOUNT_ID = sts.get_caller_identity()['Account']
REGION = boto3.session.Session().region_name or 'us-east-1'
REPO_NAME = 'fastapi-todo'
STACK_NAME = 'fastapi-todo-stack'

print("=" * 70)
print("DESPLEGANDO PRÁCTICA 2 - Container TODO")
print("=" * 70)

# 1. Crear repositorio ECR
print("\n1️⃣  Creando repositorio ECR...")
try:
    ecr.create_repository(repositoryName=REPO_NAME)
    print(f"    Repositorio {REPO_NAME} creado")
except ecr.exceptions.RepositoryAlreadyExistsException:
    print(f"    Repositorio {REPO_NAME} ya existe")

# 2. Login a ECR
print("\n  Autenticando en ECR...")
ecr_url = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com"
login_cmd = f"aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {ecr_url}"
result = subprocess.run(login_cmd, shell=True, capture_output=True, text=True)
if result.returncode == 0:
    print("   Autenticado en ECR")
else:
    print("    Error de autenticación, intentando con boto3...")
    # Alternativa con boto3
    token = ecr.get_authorization_token()['authorizationData'][0]['authorizationToken']
    import base64
    user, password = base64.b64decode(token).decode('utf-8').split(':')
    login_cmd = f"echo {password} | docker login --username {user} --password-stdin {ecr_url}"
    subprocess.run(login_cmd, shell=True)

# 3. Tag y push de imagen
print("\n  Subiendo imagen a ECR...")
image_uri = f"{ecr_url}/{REPO_NAME}:latest"
subprocess.run(f"docker tag fastapi-todo:latest {image_uri}", shell=True, check=True)
subprocess.run(f"docker push {image_uri}", shell=True, check=True)
print(f"    Imagen subida: {image_uri}")

# 4. Obtener VPC y Subnets por defecto
print("\n Obteniendo VPC y Subnets...")
vpcs = ec2.describe_vpcs(Filters=[{'Name': 'is-default', 'Values': ['true']}])
if not vpcs['Vpcs']:
    print("    No se encontró VPC por defecto")
    exit(1)
vpc_id = vpcs['Vpcs'][0]['VpcId']
print(f"    VPC: {vpc_id}")

subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
subnet_ids = [s['SubnetId'] for s in subnets['Subnets'][:2]]
print(f"    Subnets: {', '.join(subnet_ids)}")

# 5. Desplegar CloudFormation
print("\n  Desplegando stack CloudFormation...")
template_path = os.path.join(os.path.dirname(__file__), 'infra', 'fastapi-todo.yaml')
with open(template_path, 'r') as f:
    template_body = f.read()

lab_role_arn = f"arn:aws:iam::{ACCOUNT_ID}:role/LabRole"

try:
    cfn.create_stack(
        StackName=STACK_NAME,
        TemplateBody=template_body,
        Parameters=[
            {'ParameterKey': 'VpcId', 'ParameterValue': vpc_id},
            {'ParameterKey': 'SubnetIds', 'ParameterValue': ','.join(subnet_ids)},
            {'ParameterKey': 'ImageUri', 'ParameterValue': image_uri},
            {'ParameterKey': 'LabRoleArn', 'ParameterValue': lab_role_arn}
        ],
        Capabilities=['CAPABILITY_IAM']
    )
    print(f"    Creando stack {STACK_NAME}...")
except cfn.exceptions.AlreadyExistsException:
    print(f"    Stack ya existe, actualizando...")
    try:
        cfn.update_stack(
            StackName=STACK_NAME,
            TemplateBody=template_body,
            Parameters=[
                {'ParameterKey': 'VpcId', 'ParameterValue': vpc_id},
                {'ParameterKey': 'SubnetIds', 'ParameterValue': ','.join(subnet_ids)},
                {'ParameterKey': 'ImageUri', 'ParameterValue': image_uri},
                {'ParameterKey': 'LabRoleArn', 'ParameterValue': lab_role_arn}
            ],
            Capabilities=['CAPABILITY_IAM']
        )
    except cfn.exceptions.ClientError as e:
        if 'No updates are to be performed' in str(e):
            print("     Stack ya está actualizado")
        else:
            raise

# Esperar a que el stack esté listo
waiter = cfn.get_waiter('stack_create_complete')
print("   Esperando a que el stack esté listo (esto puede tomar 3-5 minutos)...")
try:
    waiter.wait(StackName=STACK_NAME, WaiterConfig={'Delay': 15, 'MaxAttempts': 40})
except Exception:
    # Puede ser update en lugar de create
    pass

# 6. Obtener outputs
print("\n  Obteniendo información del despliegue...")
time.sleep(5)
stack = cfn.describe_stacks(StackName=STACK_NAME)['Stacks'][0]
if stack['StackStatus'] in ['CREATE_COMPLETE', 'UPDATE_COMPLETE']:
    outputs = {o['OutputKey']: o['OutputValue'] for o in stack.get('Outputs', [])}
    alb_dns = outputs.get('LoadBalancerDNS', 'N/A')
    
    print("\n" + "=" * 70)
    print(" DESPLIEGUE COMPLETADO")
    print("=" * 70)
    print(f"\n URLs para capturar evidencias:")
    print(f"   API Base:    http://{alb_dns}")
    print(f"   Swagger UI:  http://{alb_dns}/docs")
    print(f"   GET Tasks:   http://{alb_dns}/tasks")
    print(f"   Health:      http://{alb_dns}/")
    print("\n Espera 1-2 minutos para que el servicio ECS esté completamente listo")
    print("=" * 70)
else:
    print(f"     Stack en estado: {stack['StackStatus']}")
    print("   Revisa la consola de CloudFormation para más detalles")
