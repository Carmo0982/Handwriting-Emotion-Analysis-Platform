# Handwriting Emotion Analysis Platform

Plataforma TDSE para analizar emociones a partir de imagenes de escritura manual. El sistema recibe una imagen, la asocia a un usuario y tenant, la guarda en almacenamiento compatible con S3, la procesa con OpenCV, ejecuta inferencia con un modelo de ML y expone los resultados por una API REST segura.

El proyecto esta construido como una arquitectura de microservicios orientada a eventos. En local corre con Docker Compose usando PostgreSQL, MinIO, Kafka y DynamoDB Local. Para produccion incluye infraestructura en AWS con Terraform, manifiestos Kubernetes, chart Helm y pipelines de GitHub Actions.

## Flujo General

```mermaid
flowchart LR
    User[Usuario autenticado] --> Auth[auth-service]
    User --> Upload[upload-service]
    Upload --> S3[(MinIO / S3)]
    Upload --> Kafka1[Kafka: image-uploaded]
    Kafka1 --> Prep[preprocessing-service]
    Prep --> S3
    Prep --> Kafka2[Kafka: image-preprocessed]
    Kafka2 --> Infer[inference-service]
    Infer --> Dynamo[(DynamoDB)]
    User --> Results[results-service]
    Results --> Dynamo
```

1. El usuario se registra e inicia sesion en `auth-service`.
2. El usuario sube una imagen PNG o JPEG a `upload-service`.
3. La imagen se valida, se guarda en S3/MinIO con ruta por `tenant_id/user_id/image_id.png` y se publica el evento `image-uploaded`.
4. `preprocessing-service` consume el evento, descarga la imagen, la convierte a escala de grises, reduce ruido, binariza, redimensiona a `224x224` y sube una version procesada.
5. `inference-service` consume `image-preprocessed`, carga el modelo y calcula probabilidades para `neutral`, `anxiety`, `stress` y `depression`.
6. El resultado se guarda en DynamoDB.
7. `results-service` permite consultar el resultado, listar historial, filtrar por emocion/fecha y obtener resumenes por usuario.

## Servicios

| Servicio | Puerto local | Responsabilidad |
| --- | ---: | --- |
| `auth-service` | `8001` | Registro, login, JWT, usuarios y tenants sobre PostgreSQL. |
| `upload-service` | `8002` | Carga segura de imagenes, validacion de tipo/tamano, almacenamiento en S3/MinIO y publicacion a Kafka. |
| `preprocessing-service` | `8003` | Consumidor Kafka que transforma imagenes con OpenCV y publica el evento de imagen procesada. |
| `inference-service` | `8004` | Consumidor Kafka que ejecuta inferencia de emociones y persiste resultados. Puede usar modelo real o motor dummy si no hay checkpoint local. |
| `results-service` | `8005` | API REST tenant-aware para consultar resultados, listas filtradas y resumenes. |

Servicios de soporte en local:

| Componente | Puerto | Uso |
| --- | ---: | --- |
| PostgreSQL | `5432` | Base de usuarios y tenants. |
| MinIO | `9000`, consola `9001` | Almacenamiento compatible con S3 para imagenes originales/procesadas. |
| Kafka | `9092` | Bus de eventos del pipeline. |
| Kafka UI | `8080` | Interfaz para inspeccionar topics y mensajes. |
| DynamoDB Local | `8000` | Resultados de inferencia. |

## Que Se Implemento

- Microservicios FastAPI separados por dominio: autenticacion, carga, preprocesamiento, inferencia y resultados.
- Autenticacion con JWT y aislamiento por tenant en endpoints protegidos.
- Persistencia de usuarios y tenants en PostgreSQL, con tenant local inicial en `infra/postgres/init.sql`.
- Carga de imagenes PNG/JPEG con limite de 10 MB.
- Almacenamiento de imagenes en rutas separadas por tenant y usuario.
- Pipeline asyncrono con Kafka usando los topics `image-uploaded` e `image-preprocessed`.
- Preprocesamiento reproducible con OpenCV: decodificacion, escala de grises, blur, threshold adaptativo, resize a `224x224` y salida PNG.
- Modelo de ML en PyTorch con backbone EfficientNet-B0, proyeccion de parches y encoder Transformer.
- Entrenamiento K-Fold, checkpoints, metricas en JSON y evaluacion con F1 macro.
- Motor de inferencia que carga checkpoints locales o desde S3 y devuelve scores por clase.
- Fallback de inferencia dummy para desarrollo local cuando no existe un modelo entrenado.
- Persistencia de resultados en DynamoDB con `tenant_id` como particion e `image_id` como rango.
- API de resultados con consulta individual, listado paginado, filtros y resumen de distribucion emocional.
- Pruebas unitarias por servicio, pruebas de ML y pruebas end-to-end del flujo completo.
- Pruebas de aislamiento multi-tenant, incluyendo cargas concurrentes de dos tenants.
- Entorno local completo con `docker-compose.yml`.
- Inicializadores locales para PostgreSQL, MinIO, Kafka topics y DynamoDB.
- Infraestructura productiva en AWS con Terraform: VPC, subredes, S3, DynamoDB, ECR, EKS, RDS, MSK y Secrets Manager.
- Manifiestos Kubernetes y Kustomize para despliegue en EKS.
- Chart Helm parametrizable por servicio.
- Pipelines de GitHub Actions para CI, build de imagenes, despliegue, Terraform y entrenamiento de modelo.
- Guia de despliegue en `.github/DEPLOYMENT.md`.
- Ajuste reciente del almacenamiento local: los defaults y `.env.example` quedaron alineados con MinIO usando `S3_BUCKET_NAME=tdse-images`, `S3_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY`. Esto evita el error `502 Image storage failed` causado por bucket o credenciales inconsistentes.

## Estructura Del Repositorio

```text
.
├── services/
│   ├── auth-service/
│   ├── upload-service/
│   ├── preprocessing-service/
│   ├── inference-service/
│   └── results-service/
├── ml/
│   ├── model/
│   ├── training/
│   ├── inference/
│   └── tests/
├── tests/e2e/
├── infra/
│   ├── postgres/
│   ├── minio/
│   ├── kafka/
│   ├── dynamodb/
│   └── k8s/
├── infrastructure/
│   ├── terraform/
│   ├── kubernetes/
│   └── helm/
├── scripts/
├── docker-compose.yml
└── .github/workflows/
```

## Requisitos

- Docker y Docker Compose.
- Python 3.11 para ejecutar pruebas y scripts fuera de contenedores.
- Terraform, AWS CLI, kubectl y Helm solo para flujos de infraestructura/despliegue.

## Ejecucion Local

1. Crear variables locales:

```bash
cp .env.example .env
```

2. Levantar todo el stack:

```bash
docker compose up --build
```

3. Revisar health checks:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

4. Abrir documentacion interactiva:

- Auth: `http://localhost:8001/docs`
- Upload: `http://localhost:8002/docs`
- Preprocessing: `http://localhost:8003/docs`
- Inference: `http://localhost:8004/docs`
- Results: `http://localhost:8005/docs`
- MinIO console: `http://localhost:9001`
- Kafka UI: `http://localhost:8080`

Credenciales locales por defecto de MinIO:

```text
usuario: minioadmin
clave: minioadmin
bucket: tdse-images
```

## Variables Principales

Las apps leen variables con los mismos nombres que aparecen en `.env.example`:

| Variable | Descripcion | Valor local |
| --- | --- | --- |
| `DATABASE_URL` | Conexion async a PostgreSQL para `auth-service`. | `postgresql+asyncpg://user:pass@postgres:5432/tdse` |
| `SECRET_KEY` / `JWT_SECRET_KEY` | Secreto de firma JWT. | `dev-secret-key-change-in-production` |
| `KAFKA_BOOTSTRAP_SERVERS` | Brokers Kafka. | `kafka:9092` en Docker, `localhost:9092` fuera de Docker |
| `S3_ENDPOINT_URL` | Endpoint S3 compatible. | `http://minio:9000` en Docker, `http://localhost:9000` fuera de Docker |
| `S3_BUCKET_NAME` | Bucket de imagenes. | `tdse-images` |
| `AWS_ACCESS_KEY_ID` | Access key para MinIO/S3. | `minioadmin` |
| `AWS_SECRET_ACCESS_KEY` | Secret key para MinIO/S3. | `minioadmin` |
| `DYNAMODB_ENDPOINT_URL` | Endpoint DynamoDB. | `http://dynamodb-local:8000` en Docker |
| `DYNAMODB_TABLE_NAME` | Tabla de resultados. | `inference-results` |
| `MODEL_PATH` | Checkpoint del modelo. | `/app/models/emotion_model.pt` |

## Uso Rapido Del Pipeline

El script `scripts/e2e_local_test.py` registra un usuario, obtiene JWT, sube una imagen PNG generada en memoria y espera el resultado:

```bash
python3 scripts/e2e_local_test.py
```

El tenant local inicial es:

```text
11111111-1111-1111-1111-111111111111
```

Tambien puedes llamar los endpoints manualmente:

```bash
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@tdse.local",
    "password": "StrongPass123",
    "tenant_id": "11111111-1111-1111-1111-111111111111"
  }'

TOKEN=$(curl -s -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@tdse.local","password":"StrongPass123"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl -X POST http://localhost:8002/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample.png;type=image/png"
```

## Pruebas

Pruebas por servicio:

```bash
cd services/upload-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests
```

El mismo patron aplica a `auth-service`, `preprocessing-service`, `inference-service` y `results-service`.

Pruebas de ML:

```bash
pip install -r ml/requirements.txt pytest pytest-cov
pytest ml/tests
```

Pruebas end-to-end con el stack local levantado:

```bash
export TEST_TENANT_A_ID=11111111-1111-1111-1111-111111111111
export TEST_TENANT_B_ID=<otro-tenant-activo-en-postgres>
pytest tests/e2e
```

## Entrenamiento Del Modelo

El dataset debe estar organizado por carpetas de clase:

```text
dataset/
├── neutral/
├── anxiety/
├── stress/
└── depression/
```

Entrenar localmente:

```bash
pip install -r ml/requirements.txt
python3 -m ml.training.train \
  --data-dir dataset \
  --epochs 50 \
  --k-folds 5 \
  --checkpoint-dir checkpoints \
  --metrics-output training_metrics.json
```

El modelo de inferencia espera imagenes `224x224` y devuelve:

```json
{
  "emotion": "neutral",
  "confidence": 0.87,
  "scores": {
    "neutral": 0.87,
    "anxiety": 0.05,
    "stress": 0.06,
    "depression": 0.02
  }
}
```

## Infraestructura Y Despliegue

El repositorio incluye dos niveles de infraestructura:

- `docker-compose.yml`: entorno local completo para desarrollo.
- `infrastructure/terraform`: recursos AWS productivos.
- `infrastructure/kubernetes`: manifiestos Kubernetes productivos para EKS.
- `infra/k8s`: base Kustomize alternativa para EKS.
- `infrastructure/helm/tdse-service`: chart Helm reutilizable por servicio.

Terraform crea o configura:

- VPC publica/privada.
- S3 para imagenes.
- DynamoDB para resultados.
- ECR para imagenes Docker.
- EKS para workloads.
- RDS PostgreSQL para autenticacion.
- MSK para Kafka.
- Secrets Manager para secretos de base de datos y JWT.

Ver detalles en:

- `infrastructure/README.md`
- `infra/k8s/README.md`
- `.github/DEPLOYMENT.md`

## CI/CD

GitHub Actions cubre:

- `CI - Tests y validacion`: pruebas por servicio, pruebas ML, cobertura, `flake8`, `black --check`, `mypy`, `bandit` y `safety`.
- `Build - Construccion de imagenes Docker`: build y push a ECR con tags `latest` y `sha-<commit>`.
- `Deploy - Despliegue a EKS`: despliegue con Helm, espera de rollout, health checks y rollback automatico por servicio.
- `Infrastructure - Cambios de Terraform`: `terraform init`, `validate`, `plan` y `apply` controlado.
- `ML - Entrenamiento del modelo`: descarga dataset desde S3, entrena K-Fold, evalua F1 macro y publica checkpoint si cumple umbral.

## Notas De Operacion

- Si `upload-service` devuelve `502` con `Image storage failed`, revisar primero que MinIO/S3 este disponible, que exista el bucket `tdse-images` y que las credenciales coincidan.
- Si el servicio corre dentro de Docker, el endpoint S3 debe ser `http://minio:9000`.
- Si corre fuera de Docker, el endpoint S3 debe ser `http://localhost:9000`.
- `inference-service` puede arrancar sin checkpoint real si `USE_DUMMY_MODEL_IF_MISSING=true`; esto sirve para validar el pipeline completo en local.
- Los resultados estan aislados por tenant y usuario. Un usuario no debe poder consultar imagenes ni resumenes de otro tenant.
