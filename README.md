# Proyectos AWS - Arquitecturas Cloud Modernas

Este repositorio contiene dos soluciones completas de arquitectura cloud en AWS, demostrando las mejores prácticas en **arquitectura serverless** y **contenedores orquestados**.

## Índice

- [Proyectos Incluidos](#proyectos-incluidos)
- [Bondades de las Soluciones](#bondades-de-las-soluciones)
- [Requisitos Previos](#requisitos-previos)
- [Configuración Inicial](#configuración-inicial)
- [Despliegue Rápido](#despliegue-rápido)
- [Características Técnicas](#características-técnicas)
- [Arquitecturas](#arquitecturas)

---

## Proyectos Incluidos

### 1. Inventario Serverless (`serverless_inventory/`)
Sistema de gestión de inventario completamente serverless con ingesta automática de datos, API REST y notificaciones en tiempo real.

**Tecnologías:** S3, Lambda, DynamoDB, API Gateway, SNS

### 2. API TODO Containerizada (`aws_container_todo/`)
API REST de gestión de tareas desplegada en contenedores con orquestación automática y alta disponibilidad.

**Tecnologías:** ECS Fargate, ECR, Application Load Balancer, MySQL

---

## Bondades de las Soluciones

### Despliegue Automatizado de un Solo Comando
- **Cero configuración manual**: Ambos proyectos se despliegan con `python deploy.py`
- **Infrastructure as Code**: Todo definido en código (CloudFormation + Python)
- **Idempotencia**: Puedes ejecutar el despliegue múltiples veces sin errores

### Optimización de Costos
- **Serverless**: Pago únicamente por uso real (Inventario)
- **Sin servidores 24/7**: Lambda se ejecuta solo cuando hay peticiones
- **Fargate Spot** compatible: Reducción de hasta 70% en costos de contenedores
- **Escalado automático**: No pagas por capacidad ociosa

### Seguridad Incorporada
- **Principle of Least Privilege**: Roles IAM con permisos mínimos necesarios
- **Security Groups**: Control granular de tráfico de red
- **CORS configurado**: Protección contra ataques cross-origin
- **VPC aislamiento**: Contenedores en red privada

### Escalabilidad Ilimitada
- **Auto-scaling**: DynamoDB escala automáticamente con la carga
- **ECS Service Auto Scaling**: Contenedores se replican según demanda
- **Lambda concurrencia**: Miles de ejecuciones simultáneas
- **ALB**: Distribución inteligente de carga entre contenedores

### Operaciones Simplificadas
- **Monitoreo integrado**: CloudWatch Logs y Metrics automáticos
- **Health Checks**: Detección y recuperación automática de fallos
- **Rollback sencillo**: Versionado de imágenes y configuraciones
- **Cero downtime**: Despliegues sin interrupciones de servicio

### Arquitecturas Modernas
- **Event-Driven**: Respuesta automática a eventos (S3 uploads, DynamoDB Streams)
- **Microservicios**: Componentes desacoplados y reutilizables
- **API-First**: Interfaces REST bien documentadas (OpenAPI/Swagger)
- **Stateless**: Aplicaciones sin estado para máxima escalabilidad

### Producción Ready
- **Retry Logic**: Reintentos automáticos en conexiones de DB
- **Circuit Breakers**: Protección contra fallos en cascada
- **Logging estructurado**: Trazabilidad completa de operaciones
- **Documentación interactiva**: Swagger UI para testing inmediato

---

## Requisitos Previos

### Software Necesario

| Herramienta | Versión | Uso |
|-------------|---------|-----|
| **Python** | 3.11+ | Scripts de despliegue |
| **Docker Desktop** | Latest | Build y push de imágenes (solo TODO API) |
| **AWS CLI** | 2.x | (Opcional) Gestión avanzada |
| **Git** | Latest | Clonar repositorio |

### Credenciales AWS

Necesitas una cuenta AWS (AWS Academy Learner Lab compatible) con:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` (para AWS Academy)
- `AWS_DEFAULT_REGION` (recomendado: `us-east-1`)

---

## Configuración Inicial

### Paso 1: Clonar el Repositorio

```powershell
git clone <URL_REPOSITORIO>
cd AWS
```

### Paso 2: Configurar Credenciales AWS

Crea un archivo `.env` en la raíz del workspace:

```env
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_SESSION_TOKEN=FwoGZXIvYXdzEBaa...
AWS_DEFAULT_REGION=us-east-1
```

### Paso 3: Cargar Variables de Entorno

**En PowerShell (Windows):**
```powershell
Get-Content .env | ForEach-Object { 
    if ($_ -match '^([^=]+)=(.*)$') { 
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2], 'Process') 
    } 
}
```

**En Bash (Linux/Mac):**
```bash
export $(cat .env | xargs)
```

### Paso 4: Instalar Dependencias Python

```powershell
pip install boto3 python-dotenv
```

**Para TODO API (adicional):**
```powershell
cd aws_container_todo/app
pip install -r requirements.txt
cd ../..
```

### Paso 5: Verificar Docker (Solo para TODO API)

```powershell
docker --version
docker ps  # Debe conectar sin errores
```

---

## Despliegue Rápido

### Proyecto 1: Inventario Serverless

**Tiempo estimado:** 2-3 minutos

```powershell
cd serverless_inventory/infra
python deploy.py
```

**Salida esperada:**
```
Upload Bucket: inventory-uploads-abc123
Website URL: http://inventory-web-abc123.s3-website-us-east-1.amazonaws.com
API URL: https://xyz789.execute-api.us-east-1.amazonaws.com
SNS Topic ARN: arn:aws:sns:us-east-1:123456:NoStock
```

**Probar la solución:**

1. **Subir CSV de inventario:**
   ```powershell
   cd ..  # Volver a serverless_inventory/
   python check.py  # Script helper para subir samples/inventory-sample.csv
   ```

2. **Ver datos en la web:**
   - Abrir la **Website URL** en tu navegador
   - Deberías ver el inventario de Berlín y Madrid

3. **Consultar API directamente:**
   ```powershell
   curl https://<API_URL>/items
   curl https://<API_URL>/items/Berlin
   ```

**Limpieza de recursos:**
```powershell
cd infra
python destroy.py
```

---

### Proyecto 2: TODO API Containerizada

**Tiempo estimado:** 4-6 minutos

```powershell
cd aws_container_todo
python deploy.py
```

**Salida esperada:**
```
API Base:    http://fastapi-todo-alb-xyz.us-east-1.elb.amazonaws.com
Swagger UI:  http://fastapi-todo-alb-xyz.us-east-1.elb.amazonaws.com/docs
GET Tasks:   http://fastapi-todo-alb-xyz.us-east-1.elb.amazonaws.com/tasks
```

**Esperar 1-2 minutos adicionales** para que ECS complete la inicialización del servicio.

**Probar la solución:**

1. **Health Check:**
   ```powershell
   curl http://<ALB_DNS>/
   # Respuesta: {"message": "CloudTasks TODO API is running"}
   ```

2. **Crear una tarea:**
   ```powershell
   curl -X POST http://<ALB_DNS>/tasks `
     -H "Content-Type: application/json" `
     -d '{"title": "Estudiar AWS", "description": "Completar prácticas", "completed": false}'
   ```

3. **Listar tareas:**
   ```powershell
   curl http://<ALB_DNS>/tasks
   ```

4. **Interfaz Swagger (recomendado):**
   - Abrir `http://<ALB_DNS>/docs` en el navegador
   - Interfaz interactiva para probar todos los endpoints

**Limpieza de recursos:**
```powershell
# Eliminar stack de CloudFormation
aws cloudformation delete-stack --stack-name fastapi-todo-stack

# Eliminar imágenes de ECR (opcional)
aws ecr delete-repository --repository-name fastapi-todo --force
```

---

## Características Técnicas

### Inventario Serverless

| Componente | Propósito | Configuración Destacada |
|------------|-----------|------------------------|
| **S3 Upload Bucket** | Ingesta de CSV | Event notification → Lambda |
| **Lambda load_inventory** | Parser y ETL | Python 3.11, 512 MB RAM, timeout 60s |
| **DynamoDB** | Base de datos NoSQL | PAY_PER_REQUEST, Streams habilitados |
| **Lambda get_inventory_api** | API Backend | Integración con API Gateway |
| **API Gateway HTTP** | Exposición pública | CORS, 2 rutas (GET /items, /items/{store}) |
| **S3 Web Bucket** | Hosting estático | Website hosting, index.html SPA |
| **Lambda notify_low_stock** | Notificaciones | Triggered por DynamoDB Streams |
| **SNS Topic** | Pub/Sub | Email subscriptions para alertas |

**Ventajas:**
- Sin gestión de servidores
- Escalado automático e ilimitado
- Pago por uso (centavos por miles de peticiones)
- Alta disponibilidad multi-AZ por defecto

---

### TODO API Containerizada

| Componente | Propósito | Configuración Destacada |
|------------|-----------|------------------------|
| **ECS Fargate** | Orquestación contenedores | Sin EC2, sin gestión de infraestructura |
| **ECR** | Registry privado | Imágenes Docker versionadas |
| **Application Load Balancer** | Balanceo de carga | Health checks, sticky sessions |
| **FastAPI Container** | API REST | Python 3.9, Uvicorn ASGI server |
| **MySQL Container** | Base de datos | Sidecar pattern, MySQL 8.0 |
| **Security Groups** | Firewall | Control granular de puertos |
| **CloudWatch Logs** | Observabilidad | Logs centralizados de contenedores |

**Ventajas:**
- Portabilidad completa (funciona idéntico local y en cloud)
- Escalado horizontal automático
- Zero downtime deployments
- Aislamiento de procesos (contenedores)

---

## Arquitecturas

### Arquitectura Serverless (Inventario)

```
┌─────────────┐
│   Usuario   │
└──────┬──────┘
       │ Sube CSV
       ▼
┌─────────────────────────┐
│  S3 Upload Bucket       │
│  (inventory-uploads-*)  │
└──────────┬──────────────┘
           │ S3 Event
           ▼
    ┌──────────────────┐
    │ Lambda Load      │──────────┐
    │ (load_inventory) │          │ Escribe
    └──────────────────┘          ▼
                          ┌───────────────┐
                          │   DynamoDB    │
                          │  (Inventory)  │
                          └───────┬───────┘
                                  │ Streams
                  ┌───────────────┼────────────────┐
                  │               │                │
                  ▼               ▼                ▼
         ┌────────────────┐  ┌─────────┐  ┌──────────────┐
         │ Lambda Notify  │  │   API   │  │  Consultas   │
         │(notify_low_st*)│  │ Gateway │  │   Usuario    │
         └────────┬───────┘  └────┬────┘  └──────────────┘
                  │               │
                  ▼               ▼
            ┌─────────┐    ┌─────────────┐
            │   SNS   │    │   Lambda    │
            │(NoStock)│    │  Get API    │
            └─────────┘    └──────┬──────┘
                                  │ Lee
                                  ▼
                          ┌───────────────┐
                          │  S3 Web       │
                          │ (index.html)  │
                          └───────────────┘
                                  ▲
                                  │ Accede
                           ┌──────────────┐
                           │   Usuario    │
                           │  (Navegador) │
                           └──────────────┘
```

**Flujo de datos:**
1. Usuario sube `inventory.csv` a S3 Upload Bucket
2. S3 dispara Lambda `load_inventory`
3. Lambda parsea CSV y carga datos en DynamoDB
4. DynamoDB Streams notifica cambios a Lambda `notify_low_stock`
5. Si stock < 5, SNS envía alerta por email
6. Usuario accede a web estática en S3
7. JavaScript llama a API Gateway
8. API Gateway ejecuta Lambda `get_inventory_api`
9. Lambda consulta DynamoDB y devuelve JSON

---

### Arquitectura Contenedores (TODO API)

```
                    Internet
                        │
                        ▼
              ┌─────────────────┐
              │  Application    │
              │  Load Balancer  │
              │  (Puerto 80)    │
              └────────┬────────┘
                       │ Health Check: /
                       │ Target: Puerto 8000
                       │
            ┌──────────┴──────────┐
            │                     │
            ▼                     ▼
   ┌────────────────┐    ┌────────────────┐
   │  ECS Service   │    │  ECS Service   │
   │   (Task 1)     │    │   (Task 2)     │ ◄─── Auto Scaling
   └───────┬────────┘    └───────┬────────┘
           │                     │
           ▼                     ▼
   ┌─────────────────────────────────┐
   │      ECS Task Definition        │
   │  ┌───────────┐  ┌────────────┐ │
   │  │  FastAPI  │  │   MySQL    │ │
   │  │Container  │  │ Container  │ │
   │  │(Port 8000)├──┤(Port 3306) │ │
   │  └───────────┘  └────────────┘ │
   │         localhost network       │
   └─────────────────────────────────┘
           │
           ▼
   ┌─────────────────┐
   │  CloudWatch     │
   │  Logs Groups    │
   └─────────────────┘
```

**Flujo de petición:**
1. Cliente HTTP → ALB (puerto 80)
2. ALB distribuye carga → ECS Service (múltiples Tasks)
3. Task recibe petición en contenedor FastAPI (puerto 8000)
4. FastAPI conecta a MySQL via `localhost:3306` (sidecar)
5. MySQL procesa query y devuelve resultado
6. FastAPI serializa respuesta JSON
7. ALB retorna respuesta al cliente

**Patrón Sidecar:**
- FastAPI y MySQL comparten networking namespace
- Comunicación ultra-rápida via localhost
- Ciclo de vida conjunto (ambos se inician/detienen juntos)

---

## Detalles de Implementación

### Reintentos y Resiliencia (TODO API)

El código de FastAPI incluye lógica de retry para manejar el arranque lento de MySQL:

```python
def get_db_connection():
    for _ in range(8):  # ~24s max
        try:
            return mysql.connector.connect(
                host=DB_HOST, user=DB_USER,
                password=DB_PASSWORD, database=DB_NAME,
                connection_timeout=5
            )
        except Exception as e:
            last_err = e
            time.sleep(3)
    raise last_err
```

### CORS Configurado (Inventario)

API Gateway incluye headers CORS para permitir peticiones desde el navegador:

```json
"CorsConfiguration": {
  "AllowOrigins": ["*"],
  "AllowMethods": ["GET", "OPTIONS"],
  "AllowHeaders": ["*"]
}
```

### Gestión de Estado (Deploy Scripts)

Ambos scripts de despliegue guardan estado en archivos JSON locales para mantener identificadores únicos (SUFFIX) entre ejecuciones.

---

## Documentación Adicional

### Inventario Serverless
[README detallado](serverless_inventory/README.md)

**Endpoints:**
- `GET /items` - Lista todo el inventario
- `GET /items/{store}` - Inventario de una tienda específica

### TODO API Containerizada
[README detallado](aws_container_todo/README.md)

**Endpoints:**
- `GET /` - Health check
- `GET /tasks` - Listar todas las tareas
- `POST /tasks` - Crear nueva tarea
- `GET /tasks/{id}` - Obtener tarea específica
- `PUT /tasks/{id}` - Actualizar tarea
- `DELETE /tasks/{id}` - Eliminar tarea

---

## Casos de Uso

### Inventario Serverless - Ideal para:
- E-commerce con inventario dinámico
- Cadenas de retail con múltiples tiendas
- Sistemas de alertas de stock bajo
- Dashboards de visualización en tiempo real
- Integraciones con sistemas de terceros (CSV exports)

### TODO API - Ideal para:
- Aplicaciones empresariales con alta disponibilidad
- Microservicios que requieren base de datos relacional
- Migraciones de aplicaciones legacy a cloud
- Sistemas con transacciones complejas (ACID)
- APIs con tráfico variable (auto-scaling)

---

## Consideraciones de Producción

### Limitaciones Actuales (AWS Academy)

- **Rol IAM fijo**: Se usa `LabRole` pre-existente (no podemos crear roles custom)
- **Persistencia**: MySQL en contenedor no usa volúmenes (datos se pierden al reiniciar)
- **Regiones limitadas**: Optimizado para `us-east-1`

### Mejoras Recomendadas para Producción

| Componente | Mejora | Beneficio |
|------------|--------|-----------|
| **MySQL** | Migrar a Amazon RDS | Persistencia, backups automáticos, multi-AZ |
| **Secrets** | AWS Secrets Manager | Rotación automática de contraseñas |
| **CDN** | Amazon CloudFront | Caché global, HTTPS, DDoS protection |
| **Dominios** | Route 53 + ACM | URLs personalizadas con SSL/TLS |
| **CI/CD** | CodePipeline + CodeBuild | Despliegues automáticos en git push |
| **Monitoreo** | CloudWatch Dashboards + X-Ray | Observabilidad completa, trazas distribuidas |
| **Costos** | AWS Cost Explorer + Budgets | Alertas de presupuesto, optimización |

---

## Contribuciones

Este proyecto fue desarrollado como parte de prácticas de arquitectura cloud. Para sugerencias o mejoras:

1. Fork el repositorio
2. Crea una rama (`git checkout -b feature/mejora`)
3. Commit cambios (`git commit -m 'Añadir mejora X'`)
4. Push a la rama (`git push origin feature/mejora`)
5. Abre un Pull Request

---

## Licencia

Este proyecto es de código abierto para propósitos educativos.

---

## Soporte

Si encuentras problemas:

1. Verifica que las credenciales AWS estén correctamente cargadas
2. Confirma que Docker Desktop esté ejecutándose (para TODO API)
3. Revisa los logs de CloudWatch en la consola AWS
4. Asegúrate de estar en la región `us-east-1`

**Logs útiles:**
```powershell
# Ver logs de Lambda
aws logs tail /aws/lambda/load_inventory --follow

# Ver logs de ECS
aws logs tail /ecs/fastapi-todo --follow
```

---

<div align="center">

**Desarrollado con las mejores prácticas de AWS**

Arquitecturas **Serverless** | **Contenedores** | **Infrastructure as Code**

</div>
