# Accesos y evidencias técnicas

Proyecto individual ITY1102 EP3: Preflop Six Max. Autor: Vicente Hueichapan.

## Componentes entregados

- Informe técnico PDF de diez páginas, con arquitectura, secuencia, capturas, validación, costos, referencias y declaración de uso de IA.
- Presentación PDF de seis láminas.
- Proyecto técnico: aplicación, modelo entrenado, dataset, infraestructura, pruebas y evidencia de las ejecuciones.
- Repositorio GitHub público: https://github.com/vicenteehueichapan-boop/ep3-preflop-sixmax

El repositorio es un requisito de la pauta. La copia comprimida del proyecto facilita la revisión y no sustituye el repositorio ni el sistema operativo en AWS.

## Accesos del sistema

| Servicio | Acceso |
|---|---|
| Mesa y dashboard | https://54.162.150.183/ |
| Contrato REST y Swagger | https://54.162.150.183/docs |
| OpenAPI | https://54.162.150.183/openapi.json |
| Disponibilidad del proceso | https://54.162.150.183/health/live |
| Disponibilidad de dependencias | https://54.162.150.183/health/ready |
| Modelo | Endpoint SageMaker `ep3-preflop`, región `us-east-1`; consumo privado mediante SDK e IAM |

La mesa inicia una sesión invitada automáticamente, sin formulario de login. La API conserva una cookie JWT HttpOnly/Secure y separa los análisis de cada sesión. Esta sesión no acredita identidad personal. Los accesos requieren laboratorio activo, EC2 iniciada, endpoint disponible y certificado válido. Los secretos se configuran en el entorno de ejecución y no forman parte de los archivos entregados.

## Índice de evidencia

| Elemento | Archivo o servicio |
|---|---|
| Dataset y etiquetas | `data/dataset.csv`, `data/policy.json` |
| Particiones sin clases equivalentes cruzadas | `data/splits.json` |
| Pesos e integridad del modelo | `artifacts/weights.json`, `artifacts/metadata.json` |
| Accuracy, precision, recall, F1 y matriz de confusión | `artifacts/metrics.json` |
| Historial de entrenamiento | `artifacts/training_history.json` |
| Resultados de 34 pruebas locales | `artifacts/tests-local.xml` |
| Resultados de 28 verificaciones AWS | `artifacts/cloud-smoke.json` |
| Recuperación final y corrida previa documentada | `artifacts/recovery-check.json`, `artifacts/recovery-before-readiness-fix.json` |
| Carga Locust: percentiles, throughput y errores | `artifacts/load-cloud_stats.csv`, `artifacts/load-cloud_failures.csv` |
| Métricas CloudWatch y actividades de escalado | `artifacts/cloud-metrics.json` (resumen sin identificadores internos) |
| Optimización local CPU | `artifacts/optimization-local.json` |
| Arquitectura y secuencia editables | `docs/ARQUITECTURA.md` |
| Solicitudes REST reproducibles | `docs/EP3_Postman.collection.json`, `scripts/demo_api.ps1` |
| Logs de API, publicador y worker | CloudWatch, grupo `/ep3-preflop/app` |
| Logs del modelo | CloudWatch, grupo `/aws/sagemaker/Endpoints/ep3-preflop` |

Las capturas históricas del despliegue están incorporadas al informe. La copia local del proyecto puede incluirlas también en `output/playwright`. Los logs cloud se consultan en la cuenta autorizada y tienen retención configurada de siete días. Los archivos de resultados acreditan ejecuciones previas y no garantizan la disponibilidad actual.

## Ejecución y límites

README contiene instalación, inferencia local, entrenamiento, pruebas y despliegue. El modo AWS exige SageMaker, PostgreSQL y RabbitMQ; el modo local se identifica como tal. El catálogo contiene seis situaciones preflop a 100 BB. La política es didáctica y sintética: no constituye un solver GTO ni predice rentabilidad. El benchmark de precarga es local; la carga HTTPS se generó desde EC2 y no mide la red de un alumno remoto.
