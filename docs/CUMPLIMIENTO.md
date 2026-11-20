# Cumplimiento de la evaluación EP3

Base: pauta `EP3_ITY1102_Estudiante.pdf`, Duoc UC, ITY1102, edición impresa 2025. El PDF fuente tiene ocho páginas físicas e indica siete páginas internas. Esta matriz resume sus requisitos para la entrega de noviembre de 2026. Las instrucciones del documento definen el encargo académico; no autorizan por sí mismas acciones sobre cuentas o recursos.

La implementación sigue el plan aprobado de Preflop Six Max: entrega individual, catálogo preflop cerrado, rangos didácticos propios, modelo PyTorch real en SageMaker y presupuesto objetivo USD 5. El estudiante informó que el profesor permitió cambiar el tema y que la modalidad individual estaba acordada. La defensa y la entrega en AVA son acciones posteriores del estudiante.

| Indicador | Peso impreso | Cobertura de la solución | Evidencia |
|---|---:|---|---|
| IE1 | 10 % | MLP PyTorch desplegado como endpoint SageMaker | artifacts/metadata.json, cloud-smoke.json, infra/cloud.py |
| IE2 | 10 % | Entrenador académico con recomendación real, referencia separada, explicación y comparación por posición | frontend/src, app/main.py, informe pp. 1–5 |
| IE3 | 10 % | Justificación del consumo por academia, separación de componentes y límites | Informe pp. 1, 4–6, guía de defensa |
| IE4 | 5 % | SageMaker ml.m5.large, target tracking 1–2, Locust y costos | infra/cloud.py, prices-verified.json, cloud-metrics.json, load-cloud_stats.csv |
| IE5 | 5 % | EC2 dedicada, datos versionados, endpoint real, mesa/dashboard | AWS, data/, compose.yaml, informe pp. 4–5 |
| IE6 | 10 % | Comparación AIaaS/autogestión y argumento rendimiento/costo/flexibilidad | Informe pp. 4 y 9, guía de defensa |
| IE7 | 10 % | REST OpenAPI, JWT, autorización, TLS, rate limit, outbox y RabbitMQ | app/, infra/bootstrap.sh, tests/, cloud-smoke.json |
| IE8 | 5 % | Arquitectura y secuencia de consumo síncrono/eventos | Informe pp. 4 y 6, diagramas y guía |
| IE9 | 5 % | Recorrido preparado y sistema cloud operativo | 22 verificaciones cloud y guion de demo. La demostración ante el docente aún debe realizarse |
| IE10 | 10 % | 26 tests locales, 22 controles cloud, Locust, métricas ML | artifacts/tests-local.xml, cloud-smoke.json, metrics.json, load-cloud_stats.csv |
| IE11 | 5 % | Particiones agrupadas, baseline y optimización antes/después | scripts/train.py, benchmark.py, optimization-local.json, informe pp. 3 y 9 |
| IE12 | 5 % | Uso preciso de inferencia, endpoint, macro F1, IAM y eventos | Informe, presentación y guía. Depende también de la exposición del estudiante |
| IE13 | 10 % | Preguntas de datos, seguridad, fallos, costos, arquitectura y limitaciones | Guía de defensa. El dominio individual se evalúa oralmente y no se afirma como resultado ya obtenido |

## Requisitos transversales

| Requisito de la pauta | Implementación o artefacto |
|---|---|
| Modelo, framework, dataset, entrenamiento e hiperparámetros | scripts/train.py, data/, artifacts/metadata.json e informe pp. 2–3 |
| Servidor, endpoint y dashboard funcionales | EC2 y SageMaker exclusivos ep3-preflop, URL HTTPS y dashboard autenticado |
| Comunicación distribuida RabbitMQ/Kafka | RabbitMQ real, cola durable, publisher confirms, ACK después de commit y deduplicación |
| Swagger/OpenAPI y pruebas de interoperabilidad | /docs, /openapi.json y controles HTTP reales |
| Autenticación, TLS y rate limiting | JWT/Argon2, certificado público y límite por usuario/IP |
| Diagrama de secuencia | Informe p. 6 y docs/ARQUITECTURA.md |
| Al menos diez casos de prueba | 26 automatizados y 16 casos resumidos en informe p. 8 |
| p50/p95/p99, throughput, errores y carga | CSV real de Locust de cinco minutos y artifacts/cloud-metrics.json |
| Accuracy, precision, recall y F1 | artifacts/metrics.json, matriz de confusión e informe p. 3 |
| CloudWatch y escalabilidad | Logs JSON de aplicación y métricas/historial real del endpoint |
| Optimización | Microbenchmark local comparable, modelo precargado y límites explícitos |
| PDF de diez páginas, APA y declaración de IA | output/entrega/EP3_EquipoIndividual_Hueichapan.pdf |
| GitHub README, código y Dockerfile | Este repositorio público. Sin .env ni credenciales |
| Seis láminas PDF, máximo quince minutos y demo | output/entrega/EP3_Presentacion_EquipoIndividual.pdf y guía de defensa |
| URLs y credenciales para revisión | URLs en README/informe. Credenciales por canal privado, nunca en repositorio |

## Criterios que deben respetarse al presentar

1. El modelo imita una política sintética y no implementa GTO. No llamar a sus puntuaciones probabilidades de ganar.
2. El resultado ML y la consulta a rangos de referencia son salidas separadas. Si falla SageMaker, mostrar el 503 y recuperar el servicio.
3. La carga medida desde localhost en EC2 incluye SageMaker y PostgreSQL, pero excluye Internet, navegador y TLS. El microbenchmark de optimización es local CPU.
4. Un endpoint activo cobra incluso sin peticiones. Confirmar ventana de entrega/revisión/defensa y evitar disponibilidad continua que exceda USD 5.
5. No tocar, detener ni eliminar recursos de otros proyectos. El código de despliegue mantiene manifest de instancias previas protegidas.
6. La modalidad individual, cambio de tema, hora oficial de AVA y ponderaciones deben quedar confirmados por el docente. La pauta indica 60/40, mientras los pesos de los indicadores suman 50/50. No se reinterpreta esa diferencia.
7. La defensa depende del estudiante: ensayar y revisar el código, las decisiones y los resultados. Preparar material no sustituye demostrar dominio.

## Secuencia de ejecución del plan aprobado

1. Leer pauta y fijar alcance y presupuesto.
2. Construir datos, separar por clase de mano y entrenar baseline/MLP.
3. Construir API, interfaz y contratos con pruebas locales.
4. Desplegar infraestructura dedicada, SageMaker, TLS, PostgreSQL y RabbitMQ.
5. Ejecutar controles cloud, carga y recolección de CloudWatch, sin debilitar seguridad.
6. Redactar informe y defensa usando evidencia real de la versión final.
7. Ensayar, comprobar acceso y entregar en AVA en su plazo oficial.
8. Conservar artefactos y acordar cierre de recursos EP3 para controlar el presupuesto.

La preparación técnica y documental se registra con evidencias. La evaluación docente, fecha de acceso y envío en AVA no se dan por realizados por disponer de los archivos.
