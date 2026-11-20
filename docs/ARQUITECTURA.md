# Diagramas de arquitectura y secuencia

```mermaid
flowchart LR
 U[Alumno React] -->|HTTPS y JWT| N[Nginx]
 N --> A[FastAPI]
 A -->|SDK HTTPS e IAM| M[SageMaker PyTorch]
 A --> D[(PostgreSQL)]
 D --> P[Publicador outbox]
 P -->|Publisher confirm| Q[RabbitMQ durable]
 Q -->|ACK posterior al commit| W[Worker idempotente]
 W --> D
 A --> C[CloudWatch]
 W --> C
 M --> C
 S[S3 privado dataset y modelo] --> M
```

React, Nginx, FastAPI, PostgreSQL, RabbitMQ, publicador y worker se ejecutan en la EC2 dedicada. El backend escala de forma independiente del modelo solo en una evolución futura. SageMaker tiene target tracking 1–2 instancias. Los enlaces entre contenedores de la EC2 son privados y no usan TLS interno.

```mermaid
sequenceDiagram
 participant UI as React
 participant API as FastAPI
 participant ML as SageMaker
 participant DB as PostgreSQL
 participant PUB as Publicador
 participant MQ as RabbitMQ
 participant W as Worker
 UI->>API: POST /v1/analyses con JWT
 API->>API: Autorizar y validar cartas y secuencia
 API->>ML: InvokeEndpoint firmado con IAM
 ML-->>API: Acción y versión del modelo
 API->>DB: BEGIN análisis y outbox
 DB-->>API: COMMIT
 API-->>UI: 201 resultado y referencia separada
 PUB->>DB: Leer pendientes con bloqueo
 PUB->>MQ: Evento persistente
 MQ-->>PUB: Publisher confirm
 PUB->>DB: Marcar publicado y COMMIT
 MQ->>W: Entrega de evento
 W->>DB: Registrar event_id único y estadística
 DB-->>W: COMMIT
 W-->>MQ: ACK
 UI->>API: GET /v1/dashboard
 API->>DB: Estadísticas por usuario
 DB-->>API: Historial y eventos procesados
 API-->>UI: Estado actualizado
```

Si falla la inferencia, FastAPI devuelve 503 antes de guardar un análisis. Si falla la publicación, el outbox persiste. Una caída entre confirmación RabbitMQ y commit del publicador puede causar reentrega. El consumidor deduplica mediante event_id, por lo que el efecto en estadísticas es idempotente. Tras tres errores de procesamiento, deriva a la cola ep3-preflop.failed.
