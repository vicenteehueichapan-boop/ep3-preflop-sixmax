# Guía de defensa EP3

Duración prevista: 11 minutos de exposición y demostración, hasta cuatro minutos de preguntas. Total máximo: 15 minutos. Seis láminas, incluida la portada. Revisar y ensayar personalmente antes de la evaluación.

## Preparación previa

- Activar el laboratorio con anticipación y comprobar que el endpoint ep3-preflop está InService. Arrancarlo puede tardar varios minutos.
- Abrir https://54.162.150.183/ y /docs. Verificar certificado válido sin omitir alertas del navegador.
- Tener las credenciales demo privadas, sin mostrarlas en el proyector ni pegarlas en chat, diapositivas o GitHub.
- Comprobar /health/ready y ejecutar scripts/smoke_cloud.py dentro del contenedor. Confirmar versión preflop-5b0e112653.
- Abrir el dashboard y dejar Swagger o Postman preparado con una sesión de demostración. La colección no incorpora contraseñas.
- Disponer de PDF, repositorio y copias de evidencias si cae la conexión. Las capturas son respaldo y no se describen como una demo en vivo.
- No ejecutar comandos de recursos generales ni tocar instancias de otros proyectos.

## Guion por lámina

### 1 Preflop Six Max  1 minuto

“Desarrollé un entrenador preflop para una academia de póker. Un alumno elige sus cartas y reconstruye las acciones anteriores hasta su turno. El sistema propone una acción y permite compararla con una política didáctica. El caso permite demostrar una aplicación empresarial de IA: interfaz, API, modelo alojado en AWS y registro de uso. El catálogo incluye seis situaciones a 100 BB. Los rangos son propios y simplificados. El sistema no resuelve equilibrio GTO ni mide posibilidades de ganar.”

Explicar BB como unidad de apuesta, preflop como la fase anterior a las cartas comunitarias y fold/call/raise como retirarse/pagar/subir. No dedicar más de 20 segundos a vocabulario de póker.

### 2 Arquitectura  1 minuto y 30 segundos

“React envía una petición autenticada por HTTPS a FastAPI. La API valida la mano y llama al endpoint de SageMaker con el SDK de AWS y un rol IAM. La inferencia vuelve a la API y se guarda junto con un evento pendiente en PostgreSQL. Un publicador envía el evento a RabbitMQ y un worker actualiza estadísticas. La respuesta de la jugada no espera al worker.”

“SageMaker separa la capacidad del modelo de la aplicación y administra el endpoint y su escalado. La EC2 reúne aplicación, base de datos y broker para limitar el costo del laboratorio. Eso deja un punto único de fallo. El diseño académico no tiene alta disponibilidad.”

### 3 Datos y modelo  1 minuto y 30 segundos

“Generé 169 clases de manos por seis escenarios: 1.014 registros sintéticos. La etiqueta proviene de una política definida en JSON. La red PyTorch tiene diez entradas, dos capas de 32 y 16 unidades y tres salidas. Aprende a imitar la política. No hay una API de lenguaje ni un solver oculto.”

“Agrupé por clase de mano para que variantes equivalentes no cruzaran las particiones. Reservé 156 filas para test. La accuracy fue 94,87 % y el macro F1 0,898, frente a 0,300 del baseline mayoritario. Uso macro F1 porque las clases están desbalanceadas. Call tiene solo siete ejemplos de test, lo que limita la estabilidad de esa métrica.”

### 4 Demostración  4 minutos

1. Entrar sin mostrar la contraseña. Señalar los seis asientos y las condiciones fijas.
2. Elegir apertura BTN, As y Kh. Completar folds UTG/HJ/CO. Explicar que el botón de completar secuencia solo agiliza la entrada de un estado soportado.
3. Solicitar análisis. Mostrar raise a 2,5 BB, fuente SageMaker, versión, tiempo y referencia separada. “Esta acción vino del modelo. La referencia permite comprobar si coincide.”
4. Mostrar UTG con 7s/2h para fold y BB contra BTN con 9s/9h para call de 1,5 BB. Si el tiempo es corto, dejar dos ejemplos preparados y hacer uno en vivo.
5. Abrir historial y métricas. Señalar análisis y eventos procesados. Actualizar si el worker aún no termina.
6. Abrir Swagger o Postman. Ejecutar GET /v1/catalog autenticado y POST /v1/analyses con el cuerpo de la colección. Mostrar el JSON con source, model_version, request_id y action. No exponer Authorization ni access_token en la pantalla.
7. En SageMaker mostrar ep3-preflop InService y la evidencia del escalado de una a dos instancias. No abrir menús de eliminación ni ajustes durante la defensa.

Si falla AWS: explicar el error real y comprobar health, laboratorio y endpoint. La API responde 503 y no inventa una recomendación. Mostrar evidencia de una ejecución previa solo como respaldo histórico.

### 5 Pruebas y optimización  1 minuto y 30 segundos

“Ejecuté 26 tests locales de reglas, contratos y seguridad, además de 22 verificaciones cloud reales. Locust generó cinco usuarios por cinco minutos: 1.464 solicitudes, cero fallos y 4,89 solicitudes por segundo. p50/p95/p99 fueron 20/35/110 ms.”

“El generador corrió en la EC2 contra la API local. Incluye el viaje de inferencia a SageMaker y la base de datos, pero no Internet, Nginx ni el navegador. No es la latencia vista por cualquier usuario externo. La política automática terminó un escalado de una a dos instancias.”

“Comparé cargar pesos por petición y reutilizar el modelo precargado con 100 ejecuciones para cada alternativa. La media local bajó de 1,348 a 0,086 ms. Es un microbenchmark CPU que justifica la precarga. No lo presento como una mejora cloud de la misma magnitud.”

### 6 Costos y límites  1 minuto

“SageMaker ml.m5.large cuesta USD 0,115 por hora e instancia en la región utilizada y EC2 t3.medium USD 0,0418 por hora. La reserva de cómputo y gastos menores del plan es aproximadamente USD 2,58, con objetivo máximo USD 5. El endpoint cobra mientras existe aunque no lo consultemos. Debo usar ventanas de demostración y una pausa autorizada de recursos EP3.”

“Esta solución cubre un catálogo pequeño, usa datos sintéticos y una sola EC2. Su evaluación mide concordancia de clasificación. Para una academia real faltan validación estratégica y educativa, gestión completa de usuarios, permisos mínimos y alta disponibilidad. Los recursos del otro proyecto permanecieron separados.”

## Preguntas frecuentes para ensayar

**¿Dónde está la IA si las etiquetas están en un JSON?** El JSON define la política supervisada. PyTorch aprende una aproximación a sus etiquetas. La API devuelve inferencia real de SageMaker y consulta el JSON por separado como referencia. Se puede observar una discrepancia. Una tabla sola resolvería este catálogo de forma exacta y más simple, pero no demostraría el requisito de ML desplegado.

**¿Por qué no llamarlo GTO?** No hay búsqueda de equilibrio, cálculo de estrategia mixta ni validación contra un solver. Son rangos didácticos fijos. GTO sería una afirmación que esta implementación no sustenta.

**¿Qué son los tres scores?** Puntuaciones normalizadas del clasificador para las acciones. No son equity, probabilidad de ganar ni una recomendación de apostar dinero. Call se excluye de escenarios donde no está admitido.

**¿Por qué 169 manos y no 1.326 combinaciones?** Agrupo manos con el mismo rango y relación de palos. Esta simplificación es válida para la política definida, que no distingue el palo específico. Las métricas ponderan clases por igual, no combinaciones reales.

**¿Cómo evitaste fuga de datos?** Separé por clase canónica de mano, manteniendo juntas sus seis situaciones. El test no selecciona hiperparámetros. La validación selecciona la época. Las etiquetas provienen de reglas conocidas y la tarea es imitación, no generalización hacia póker real.

**¿Por qué macro F1?** Da el mismo peso a fold, call y raise. La accuracy por sí sola favorece fold porque tiene 128 de los 156 casos de test. F1 combina precision y recall por clase.

**¿Qué aporta RabbitMQ?** Desacopla el análisis de la actualización de estadísticas y permite procesar eventos persistidos tras un reinicio. El outbox evita guardar un análisis sin conservar su evento. La idempotencia evita doble efecto ante una reentrega.

**¿Qué pasa si el consumidor se cae después del commit?** El broker puede reenviar si aún no recibió ACK. El event_id ya registrado impide repetir la actualización. Luego el consumidor confirma el mensaje.

**¿Qué valida TLS?** Cifra y autentica la conexión del navegador hasta Nginx. Las llamadas al endpoint usan HTTPS e IAM. Los enlaces Docker internos no usan TLS; esto es una limitación declarada del laboratorio.

**¿Qué pasa con solicitudes ajenas?** Se exige JWT y el análisis debe pertenecer al usuario. La API responde 404 ante un id ajeno para no revelar su existencia. Los límites devuelven 429 y el proveedor fallido devuelve 503.

**¿Por qué SageMaker y no solo EC2?** Es requisito del encargo y permite desacoplar el ciclo de vida y capacidad de inferencia. Para un modelo tan pequeño y volumen reducido, solo EC2 simplificaría y podría abaratar, a cambio de operar el modelo y su escalado.

**¿Es escalable toda la aplicación?** El endpoint sí tiene política 1–2 y escaló en la prueba. El backend y la base de datos siguen en una sola EC2. No afirmar escalabilidad global ni alta disponibilidad.

**¿Por qué el objetivo de 60 invocaciones por instancia y minuto?** Es un umbral conservador para observar el mecanismo de escalado dentro de la demo acotada. No representa la capacidad máxima medida del modelo ni un punto de saturación. Ajustarlo para producción exige probar más niveles de concurrencia y relacionar costo, latencia y utilización. El máximo de dos instancias protege el presupuesto del laboratorio.

**¿Cómo detener el gasto?** Detener EC2 no detiene el endpoint SageMaker. Se necesita autorización para retirar únicamente el endpoint EP3 y detener su instancia. Se conservan modelo, configuración, S3 y datos. EBS e IPv4 pueden seguir cobrando. No tocar recursos de otros proyectos.

**¿Cómo sabes que no se simuló AWS?** Las respuestas incluyen source=sagemaker y versión, la configuración production rechaza backends locales y la evidencia registra el endpoint, CloudWatch y el historial de escalado. Las pruebas cloud consumieron el endpoint real.

**¿Qué mejoraría primero?** Validar y ampliar los datos con un especialista y medir utilidad educativa. Operativamente, separar base de datos y broker, endurecer IAM y secretos, añadir TLS interno y recuperar desde copias. No añadir infraestructura costosa solo para aparentar complejidad.

## Antes de enviar en AVA

Verificar los dos PDFs y el enlace GitHub, el plazo real, los nombres requeridos y la ventana de revisión. Las seis láminas y el informe de diez páginas describen la misma versión. Entregar credenciales por el mecanismo privado que indique el docente. La pauta impresa tiene una inconsistencia entre 60/40 y los pesos de indicadores 50/50: consultar su aplicación sin reinterpretarla.
