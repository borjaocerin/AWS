# Practica 2 - Container TODO API

FastAPI TODO API desplegada en AWS ECS Fargate con MySQL en contenedor sidecar.

## Arquitectura

- ECS Fargate: Orquestacion de contenedores sin gestionar servidores
- Task Definition: 2 contenedores (FastAPI + MySQL 8.0)
- Application Load Balancer: Expone la API publicamente
- Security Groups: Control de trafico entre ALB, ECS y contenedores

## Estructura del Proyecto

```
app/
  main.py              - Aplicacion FastAPI con endpoints /tasks
  Dockerfile           - Imagen de contenedor Python 3.9
  requirements.txt     - Dependencias (fastapi, uvicorn, mysql-connector-python)

infra/
  fastapi-todo.yaml    - Plantilla CloudFormation (ECS, ALB, Security Groups)

deploy.py              - Script automatizado de despliegue completo
```

## Requisitos Previos

1. Docker Desktop instalado y en ejecucion
2. Credenciales AWS Academy en archivo .env (raiz del workspace)
3. Python 3.11+ con dependencias instaladas:
   ```
   pip install -r requirements.txt
   ```

## Despliegue Completo (Un Solo Comando)

Ejecutar desde la carpeta aws_container_todo:

```bash
python deploy.py
```

Este script automatiza:
- Creacion de repositorio ECR (si no existe)
- Autenticacion en ECR
- Build y push de imagen Docker
- Obtencion automatica de VPC y Subnets por defecto
- Despliegue de stack CloudFormation
- Configuracion de ECS Cluster, Task Definition, Service y ALB

Tiempo estimado: 3-5 minutos

## Salida del Despliegue

Al finalizar, el script muestra:

```
API Base:    http://fastapi-todo-alb-XXXXXXXXXX.us-east-1.elb.amazonaws.com
Swagger UI:  http://fastapi-todo-alb-XXXXXXXXXX.us-east-1.elb.amazonaws.com/docs
GET Tasks:   http://fastapi-todo-alb-XXXXXXXXXX.us-east-1.elb.amazonaws.com/tasks
Health:      http://fastapi-todo-alb-XXXXXXXXXX.us-east-1.elb.amazonaws.com/
```

Esperar 1-2 minutos adicionales para que el servicio ECS complete su inicializacion.

## Verificacion Manual

### Health Check
```bash
curl http://<ALB_DNS>/
```
Respuesta esperada: `{"message": "CloudTasks TODO API is running"}`

### Listar Tareas
```bash
curl http://<ALB_DNS>/tasks
```
Respuesta inicial: `[]` (array vacio)

### Crear Tarea (POST)
```bash
curl -X POST http://<ALB_DNS>/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Mi primera tarea", "description": "Probar API", "completed": false}'
```

### Swagger UI Interactivo
Abrir en navegador: `http://<ALB_DNS>/docs`

## Notas Tecnicas

- Uso de LabRole: AWS Academy Learner Lab no permite crear roles IAM personalizados. El stack usa el rol preexistente LabRole para ECS Task Execution.

- MySQL Sidecar: La base de datos MySQL 8.0 corre en un contenedor secundario dentro del mismo Task Definition, conectado via localhost.

- Retry Logic: La aplicacion FastAPI incluye logica de reintento (8 intentos x 3 segundos) para esperar a que MySQL este listo antes de crear la tabla.

- Persistencia: Los datos se pierden al reiniciar el Task (MySQL no usa volumen persistente). Para produccion, usar RDS.

## Limpieza de Recursos

Eliminar el stack de CloudFormation:

```bash
aws cloudformation delete-stack --stack-name fastapi-todo-stack
```

O mediante boto3:

```bash
python -c "import boto3; boto3.client('cloudformation').delete_stack(StackName='fastapi-todo-stack'); print('Stack eliminandose...')"
```

Verificar eliminacion completa (tarda 2-3 minutos):

```bash
aws cloudformation describe-stacks --stack-name fastapi-todo-stack
```

Eliminar repositorio ECR (opcional):

```bash
aws ecr delete-repository --repository-name fastapi-todo --force
```

## Troubleshooting

### Error: "No module named 'dotenv'"
```bash
pip install python-dotenv
```

### Error: Docker daemon not running
Iniciar Docker Desktop antes de ejecutar deploy.py

### Error: AccessDenied en CloudFormation
Verificar que las credenciales en .env sean de AWS Academy Learner Lab (no credenciales personales)

### Error: Service Unhealthy
Esperar 2-3 minutos adicionales. Revisar logs de CloudWatch:
```bash
aws logs tail /ecs/fastapi-todo --follow
```
