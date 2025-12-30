# Practica 1 - Inventario Serverless

Arquitectura serverless: S3 (ingesta CSV) → Lambda → DynamoDB → API Gateway → Web estática S3 → (opcional) SNS

## Arquitectura

- S3 Bucket Uploads: Recibe CSV con inventario
- Lambda load_inventory: Triggered por evento S3, parsea CSV y carga en DynamoDB
- DynamoDB Inventory: Almacena store + item + cantidad con Streams habilitados
- Lambda get_inventory_api: Ejecutada por API Gateway, devuelve JSON
- API Gateway HTTP: Expone 2 rutas GET /items y GET /items/{store} con CORS
- S3 Web Bucket: Hosting estático de index.html
- Lambda notify_low_stock: (Opcional) Triggered por DynamoDB Streams, publica en SNS
- SNS NoStock: Topic para notificaciones de inventario bajo

## Estructura del Proyecto

```
infra/
  deploy.py         - Orquestacion completa de recursos (Python 3.11)
  destroy.py        - Limpieza de todos los recursos

lambdas/
  load_inventory/   - Parsea CSV y carga en DynamoDB
  get_inventory_api/  - API backend para consultas
  notify_low_stock/ - Notificaciones por SNS

web/
  index.html        - SPA que consulta API con fetch

samples/
  inventory-sample.csv - Datos de prueba (Berlin y Madrid)
```

## Requisitos Previos

1. Python 3.11+ instalado
2. Credenciales AWS Academy en archivo .env (raiz del workspace):
   ```
   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   AWS_SESSION_TOKEN=...
   AWS_DEFAULT_REGION=us-east-1
   ```

3. Cargar credenciales en la sesion PowerShell:
   ```powershell
   Get-Content C:\Users\borja\Desktop\Cloud\AWS\.env | ForEach-Object { if ($_ -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') } }
   ```

4. Instalar dependencias (desde raiz del workspace):
   ```powershell
   pip install -r requirements.txt
   ```

## Despliegue Completo (Un Solo Comando)

Desde la carpeta serverless_inventory/infra:

```powershell
python deploy.py
```

Este script automatiza:
- Creacion de 2 buckets S3 (ingesta y web)
- Creacion de tabla DynamoDB con Streams
- Creacion de 3 funciones Lambda (Python 3.11)
- Creacion de API Gateway HTTP con CORS
- Deployment de website estático
- Creacion de SNS topic

Tiempo estimado: 1-2 minutos

## Salida del Despliegue

El script imprime al finalizar:

```
Upload Bucket: inventory-uploads-XXXXXX
Website URL: http://inventory-web-XXXXXX.s3-website-us-east-1.amazonaws.com
API URL: https://XXXXXXX.execute-api.us-east-1.amazonaws.com
SNS Topic ARN: arn:aws:sns:us-east-1:XXXX:NoStock
```

## Subir CSV y Activar Lambda

Opcion 1: Con boto3 (Python)

```python
import boto3
s3 = boto3.client('s3')
s3.upload_file('samples/inventory-sample.csv', 'inventory-uploads-XXXXXX', 'inventory.csv')
```

Opcion 2: Directamente con AWS CLI (si esta instalado)

```bash
aws s3 cp samples/inventory-sample.csv s3://inventory-uploads-XXXXXX/inventory.csv
```

Al subir, Lambda se ejecuta automaticamente y carga los datos en DynamoDB.

## Verificacion Manual

### Health Check API
```bash
curl https://XXXXXXX.execute-api.us-east-1.amazonaws.com/items
```
Deberia devolver JSON con el inventario cargado

### Filtrar por Store
```bash
curl https://XXXXXXX.execute-api.us-east-1.amazonaws.com/items/Berlin
```
Deberia devolver solo items de Berlin

### Web Estatica
Abrir en navegador: http://inventory-web-XXXXXX.s3-website-us-east-1.amazonaws.com

Deberia mostrar tabla con:
- Berlin: Echo Dot (12), Echo Plus (0)
- Madrid: Kindle (5)

### SNS (Opcional - Notificaciones)
Suscribirse al topic NoStock desde consola de AWS para recibir notificaciones cuando count < 5

## Limpieza de Recursos

Eliminar TODOS los recursos (buckets, DynamoDB, Lambdas, API, SNS, roles IAM):

```powershell
python destroy.py
```

El script lee deploy_state.json y elimina cada recurso en orden correcto.

## Notas Tecnicas

- Runtime: Todas las Lambdas usan Python 3.11 (especificado en deploy.py)
- IAM: Se crean 3 roles con permisos minimos:
  - load_inventory: s3:GetObject + dynamodb:PutItem
  - get_inventory_api: dynamodb:Query + dynamodb:Scan
  - notify_low_stock: dynamodb:GetRecords + sns:Publish

- CORS: API Gateway tiene AllowOrigins=['*'] para permitir fetch desde web en S3

- Idempotencia: Si se ejecuta deploy.py nuevamente, detecta recursos existentes y actualiza sin fallar

- DynamoDB Streams: Habilitados para trigger del Lambda de notificaciones

## Troubleshooting

### Error: "credentials not found"
Verificar que .env este en raiz del workspace y que las credenciales esten cargadas en la sesion PowerShell

### Error: "AccessDenied"
Verificar que se usan credenciales de AWS Academy Learner Lab (con SessionToken), no credenciales personales de AWS

### Lambda no ejecuta al subir CSV
Esperar 5-10 segundos después de subir. Revisar CloudWatch Logs en consola de AWS para ver si hay errores

### Web no carga datos
Esperar a que Lambda procese el CSV (ver CloudWatch Logs), luego refrescar navegador. Si aun no ve datos, revisar:
- Que el CSV se subio correctamente
- Que DynamoDB table contiene items
- Que la URL de API en index.html es correcta
