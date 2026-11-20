"""Informe editable de diez páginas. Ejecutar con Python de Workspace Dependencies."""
import json
from pathlib import Path

import subprocess
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from reportlab.pdfgen import canvas

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/entrega'; OUT.mkdir(parents=True,exist_ok=True)
TMP=ROOT/'tmp/report'; TMP.mkdir(parents=True,exist_ok=True)
METRICS=json.loads((ROOT/'artifacts/metrics.json').read_text())
CLOUD=json.loads((ROOT/'artifacts/cloud-metrics.json').read_text())
LOAD=next(r for r in CLOUD['load'] if r['Name']=='Aggregated')


def diagram(kind):
    path=TMP/(kind+'.pdf')
    c=canvas.Canvas(str(path),pagesize=(760,310))
    c.setFont('Helvetica',11)
    def box(x,y,w,h,label):
        c.setFillColorRGB(.94,.96,.94);c.setStrokeColorRGB(.45,.53,.47)
        c.roundRect(x,y,w,h,5,fill=1,stroke=1)
        c.setFillColorRGB(.05,.1,.07)
        for i,line in enumerate(label.split('\n')):c.drawCentredString(x+w/2,y+h/2+7-i*16,line)
    def arrow(x1,y1,x2,y2,label='',dy=8):
        c.setStrokeColorRGB(.25,.35,.28);c.line(x1,y1,x2,y2)
        if x2>x1:c.line(x2-6,y2+3,x2,y2);c.line(x2-6,y2-3,x2,y2)
        elif x2<x1:c.line(x2+6,y2+3,x2,y2);c.line(x2+6,y2-3,x2,y2)
        else:c.line(x2-3,y2+6,x2,y2);c.line(x2+3,y2+6,x2,y2)
        c.setFillColorRGB(.1,.2,.13);c.drawCentredString((x1+x2)/2,(y1+y2)/2+dy,label)
    if kind=='arquitectura':
        box(8,200,125,58,'Navegador\nReact');box(260,200,190,58,'EC2 dedicada\nNginx y FastAPI');box(600,200,150,58,'SageMaker\nPyTorch')
        box(260,45,190,58,'PostgreSQL\nAnalisis y outbox');box(580,45,170,58,'RabbitMQ y worker\nEstadisticas')
        arrow(133,228,260,228,'HTTPS');arrow(450,228,600,228,'SDK e IAM');arrow(355,200,355,103,'SQL',dy=0)
        arrow(450,74,580,74,'Eventos');arrow(580,54,450,54,'Estadisticas',dy=-14)
        c.setFont('Helvetica',10);c.drawString(8,14,'CloudWatch recibe logs de aplicacion y metricas de SageMaker. S3 conserva dataset y modelo.')
    else:
        xs=[55,206,375,530,700];labels=['React','FastAPI','SageMaker','PostgreSQL','RabbitMQ / worker']
        for x,label in zip(xs,labels):
            c.setFillColorRGB(.05,.1,.07);c.drawCentredString(x,286,label);c.setDash(2,2);c.line(x,270,x,18);c.setDash()
        arrow(xs[0],250,xs[1],250,'POST /analyses con JWT')
        arrow(xs[1],216,xs[2],216,'InvokeEndpoint')
        arrow(xs[2],184,xs[1],184,'Accion y version')
        arrow(xs[1],151,xs[3],151,'BEGIN, analisis + outbox, COMMIT')
        arrow(xs[1],119,xs[0],119,'201 con recomendacion')
        arrow(xs[3],86,xs[4],86,'Publicador confirma evento')
        arrow(xs[4],52,xs[3],52,'Idempotencia y estadistica')
    c.save()
    target=TMP/(kind+'.png')
    subprocess.run(['pdftoppm','-png','-r','144','-singlefile',str(path),str(TMP/kind)],check=True)
    return target


doc=Document();s=doc.sections[0]
s.page_height=Cm(29.7);s.page_width=Cm(21)
s.top_margin=Cm(1.65);s.bottom_margin=Cm(1.55);s.left_margin=Cm(1.8);s.right_margin=Cm(1.8)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','Caption']:
    style=doc.styles[name];style.font.name='Calibri';style.font.color.rgb=RGBColor(0,0,0)
for style in doc.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
doc.styles['Normal'].font.size=Pt(10.5)
doc.styles['Normal'].paragraph_format.space_after=Pt(6)
doc.styles['Normal'].paragraph_format.line_spacing=1.08
doc.styles['Title'].font.size=Pt(26)
doc.styles['Heading 1'].font.size=Pt(18)
doc.styles['Heading 1'].paragraph_format.space_after=Pt(10)
doc.styles['Heading 2'].font.size=Pt(12)
doc.styles['Heading 2'].paragraph_format.space_before=Pt(7)
doc.styles['Heading 2'].paragraph_format.space_after=Pt(5)
doc.styles['Caption'].font.size=Pt(8.5)
footer=s.footer.paragraphs[0];footer.alignment=2
footer.add_run('Preflop Six Max  |  EP3  |  ').font.size=Pt(8)
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)
doc.core_properties.author='Vicente Hueichapan'
doc.core_properties.title='Preflop Six Max Informe técnico EP3'


def p(text,style=None):return doc.add_paragraph(text,style)
def h(text):doc.add_heading(text,level=2)
def page(title):doc.add_page_break();doc.add_heading(title,level=1)
def table(headers,rows,widths=None):
    t=doc.add_table(rows=1,cols=len(headers));t.autofit=False
    for i,v in enumerate(headers):t.rows[0].cells[i].text=v
    for vals in rows:
        for cell,v in zip(t.add_row().cells,vals):cell.text=str(v)
    for ri,row in enumerate(t.rows):
        for ci,cell in enumerate(row.cells):
            if widths:cell.width=Cm(widths[ci])
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcPr=cell._tc.get_or_add_tcPr();borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right','insideH','insideV']:
                e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
            tcPr.append(borders)
            margins=OxmlElement('w:tcMar')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:w'),'70');e.set(qn('w:type'),'dxa');margins.append(e)
            tcPr.append(margins)
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'243B31' if ri==0 else ('F2F5F2' if ri%2==0 else 'FFFFFF'));tcPr.append(shade)
            for para in cell.paragraphs:
                para.paragraph_format.space_after=Pt(2);para.paragraph_format.space_before=Pt(2);para.paragraph_format.line_spacing=1
                for run in para.runs:
                    run.font.size=Pt(9.3);run.font.bold=ri==0;run.font.color.rgb=RGBColor(255,255,255) if ri==0 else RGBColor(0,0,0)
    trPr=t.rows[0]._tr.get_or_add_trPr();repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
    p('')
    return t
def figure(path,caption,width=6.65):
    doc.add_picture(str(path),width=Inches(width));p(caption,'Caption')

def endpoint_figure():
    shape=doc.add_picture(str(ROOT/'output/playwright/aws-sagemaker.png'),width=Inches(6.65))
    crop=OxmlElement('a:srcRect')
    for key,value in {'l':'15000','t':'9000','b':'48000','r':'0'}.items():crop.set(key,value)
    shape._inline.graphic.graphicData.pic.blipFill.insert(1,crop)
    shape.height=Inches(1.56)
    p('Figura 2. Captura real de SageMaker: ep3-preflop en servicio. Recorte del resumen del endpoint.','Caption')


p('Preflop Six Max','Title')
p('Informe técnico de despliegue y optimización de un sistema de IA','Subtitle')
p('Vicente Hueichapan\nArquitectura de Sistemas de Inteligencia Artificial · ITY1102\nEvaluación Parcial 3 · Entrega individual · Noviembre de 2026')
h('Caso empresarial y resultado')
p('El proyecto propone un entrenador para una academia de póker. El alumno construye una situación previa al flop, selecciona sus dos cartas y consulta una recomendación. El entrenador puede revisar ejercicios y concordancia con una política de referencia. El valor esperado es ofrecer práctica consistente y trazable, con una explicación que relacione mano, posición y regla de referencia. No se midió una mejora real del aprendizaje ni rentabilidad económica.')
p('La solución funciona en AWS: una interfaz React consume FastAPI en EC2 y la API obtiene la predicción real de un clasificador PyTorch alojado en SageMaker. PostgreSQL conserva los análisis. RabbitMQ comunica eventos a un worker de estadísticas. Las pruebas de integración cloud aprobaron 22 de 22 controles. El test reservado del modelo alcanzó 94,87 % de accuracy y macro F1 de 0,898.')
h('Alcance cerrado')
p('Texas Hold’em cash six max, stacks iniciales de 100 BB, ciegas 0,5/1 BB y sin antes. Se admiten cinco aperturas después de folds, desde UTG, HJ, CO, BTN y SB, y la defensa de BB frente a una apertura de BTN. La interfaz mantiene seis asientos y calcula aportes, bote y turno desde la secuencia validada.')
p('La política es didáctica y propia. El modelo aprende a imitar esas etiquetas. Las puntuaciones del clasificador no representan equity y los rangos no constituyen un equilibrio GTO. Quedan fuera postflop, torneos, ICM, otros stacks, limps, varios callers y decisiones ante resubidas sucesivas.')
table(['Servicio','Acceso'],[['Interfaz y dashboard','https://54.162.150.183/'],['API y Swagger','https://54.162.150.183/docs'],['Repositorio público','github.com/vicenteehueichapan-boop/ep3-preflop-sixmax'],['Endpoint ML','ep3-preflop en us-east-1, acceso autenticado por IAM']], [4,13.4])
p('Las URLs requieren que el laboratorio y el cómputo EP3 estén activos. Las credenciales de la cuenta demo se entregan por un canal privado y se excluyen del repositorio y del informe.')

page('2 Datos y política de referencia')
p('El archivo data/policy.json define seis situaciones. El generador expande 169 clases canónicas: 13 parejas, 78 manos suited y 78 offsuit. Cada clase aparece una vez por situación, generando 1.014 filas sintéticas. No son manos observadas ni datos de jugadores. La etiqueta es determinista y toda mano fuera de los rangos se clasifica como fold.')
table(['Situación','Raise','Call'],[
['UTG','77+, ATs+, KQs, AQo+','—'],
['HJ','66+, A9s+, KJs+, QJs, AJo+, KQo','—'],
['CO','44+, A5s+, KTs+, QTs+, JTs, T9s, ATo+, KJo+','—'],
['BTN','22+, A2s+, K8s+, Q9s+, J9s+, T8s+, 98s, A8o+, KTo+, QTo+, JTo','—'],
['SB','22+, A2s+, K7s+, Q9s+, J9s+, T8s+, 98s, A7o+, KTo+, QTo+, JTo','—'],
['BB contra BTN','TT+, AQs+, AKo','22–99, A2s–AJs, K9s+, Q9s+, J9s+, T8s+, 98s, 87s, ATo–AQo, KTo+, QTo+, JTo']], [2.7,7.3,7.4])
p('La notación s indica mismo palo y o indica palos distintos. El signo + amplía parejas hacia AA o el segundo rango hacia el primero: ATs+ corresponde a ATs, AJs, AQs y AKs. Los intervalos incluyen ambos extremos. En BB se aplica primero raise, luego call y finalmente fold. Las pruebas verifican estas expansiones y la ausencia de cartas repetidas.')
h('Entradas y tamaños')
p('La codificación usa diez valores: ambos rangos normalizados, indicador suited, indicador de pareja y seis indicadores de situación. La política fija subidas a 2,5 BB, a 3 BB desde SB y a 10 BB para la resubida de BB. La apertura de BTN más las ciegas genera un bote de 4 BB y BB debe completar 1,5 BB para pagar.')
h('Separación reproducible')
p('Con semilla 42, 118 clases de mano se asignan a entrenamiento, 25 a validación y 26 a test. Las seis situaciones de una misma clase permanecen juntas. El resultado es 708/150/156 registros, respectivamente. Así se evita que variantes equivalentes atraviesen las particiones. data/splits.json conserva la asignación y dataset.csv contiene todas las filas.')
p('El muestreo trata cada clase canónica por igual. No pondera las combinaciones físicas, que son distintas para parejas, suited y offsuit. Por ello las métricas describen este catálogo académico, no la distribución natural de manos repartidas.')

page('3 Entrenamiento y validación del modelo')
p('El clasificador utiliza PyTorch 2.9.1 CPU y una red MLP 10–32–16–3 con activaciones ReLU. El optimizador Adam usa aprendizaje 0,001, minibatches de 32 y pérdida de entropía cruzada. Se fijó un máximo de 400 épocas y parada temprana con paciencia de 60, habilitada después de 150 épocas. Se ejecutaron 270 épocas y la validación seleccionó la época 210. El entrenamiento local tardó 5,48 s.')
p('La selección usa macro F1 de validación, que alcanzó 0,9335. El test reservado se evaluó al finalizar. El baseline predice la acción mayoritaria de cada situación a partir de entrenamiento. Para impedir una acción inválida, la capa de inferencia anula call fuera del escenario BB contra BTN. En el test no aparecieron acciones ilegales antes de esta restricción.')
table(['Métrica de test','MLP','Baseline'],[['Accuracy','0,9487','0,8205'],['Precision macro','0,8804','0,2735'],['Recall macro','0,9261','0,3333'],['F1 macro','0,8979','0,3005'],['Registros de test','156','156']], [6.2,5.6,5.6])
table(['Clase','Precision','Recall','F1','Soporte'],[['Fold','0,9688','0,9688','0,9688','128'],['Call','0,7778','1,0000','0,8750','7'],['Raise','0,8947','0,8095','0,8500','21']], [4.2,3.3,3.3,3.3,3.3])
h('Errores y límites de interpretación')
p('La matriz de confusión, en orden fold/call/raise, es [[124,2,2],[0,7,0],[4,0,17]]. Ocho etiquetas difieren de la referencia. La clase call tiene solo siete ejemplos de test, por lo que su estimación es inestable. El resultado evidencia concordancia con etiquetas sintéticas, no calidad estratégica frente a oponentes ni una ventaja sobre un solver.')
h('Artefactos y versión')
p('La versión preflop-5b0e112653 deriva del SHA-256 de los pesos. artifacts/metadata.json conserva framework, semilla, hiperparámetros, particiones y huellas de política y modelo. weights.json transporta tensores del state_dict para cargarlos sin deserializar objetos Python arbitrarios. El servicio verifica la huella antes de servir predicciones. El paquete model.tar.gz se almacena en S3 y SageMaker lo monta en /opt/ml/model.')

page('4 Arquitectura y despliegue en AWS')
figure(diagram('arquitectura'),'Figura 1. Componentes realmente desplegados. La API atiende la decisión y la mensajería actualiza estadísticas.')
p('Una EC2 t3.medium con Amazon Linux 2023 ejecuta Nginx y Docker Compose. Los contenedores incluyen API/interfaz, PostgreSQL 17, RabbitMQ 4, publicador y worker. La API escucha solo en localhost:8000 del host. Los puertos de base de datos y broker no se publican a Internet. La infraestructura tiene etiquetas exclusivas Project=ep3-preflop y un grupo de seguridad propio con HTTP para ACME y HTTPS.')
p('SageMaker aloja una imagen de inferencia PyTorch CPU publicada en ECR. El contenedor expone /ping y /invocations. Su endpoint ep3-preflop usa ml.m5.large y la variante main. S3 conserva artefactos y datos con bloqueo público y cifrado AES256. La aplicación usa el SDK de AWS y el perfil de instancia del laboratorio para invocar el endpoint, sin claves AWS en el navegador.')
endpoint_figure()
p('AIaaS separa la capacidad de inferencia del servidor web. SageMaker facilita endpoint, métricas y escalado administrado, aunque cobra por el tiempo provisionado (Amazon Web Services, s.f.-c). Alojar la misma red en EC2 reduciría componentes y puede convenir para este volumen bajo, pero obligaría a operar su escalado y disponibilidad. Aquí SageMaker también responde al requisito explícito de la evaluación.')
p('El diseño de una sola EC2 limita disponibilidad y escalabilidad del backend. El rol LabRole pertenece al laboratorio y tiene permisos más amplios que un rol de producción mínimo. El proyecto no cambió políticas IAM ni recursos de las otras aplicaciones. Una evolución empresarial separaría base de datos y broker, añadiría alta disponibilidad y restringiría IAM por recurso.')

page('5 Interfaz e interpretación de resultados')
shot=ROOT/'output/playwright/aws-mesa.png'
if not shot.exists():shot=ROOT/'output/playwright/aws-login.png'
figure(shot,'Figura 3. Interfaz servida por HTTPS desde la instancia dedicada en AWS.',6.65)
p('La mesa muestra UTG, HJ, CO, BTN, SB y BB. El usuario escoge una situación del catálogo y dos cartas distintas entre 52 opciones. Puede completar las acciones anteriores una por una o aplicar la secuencia prevista. La API vuelve a validar la secuencia, de modo que el navegador no determina por sí solo si el estado es legal.')
p('La recomendación muestra la acción del modelo, tamaño si corresponde, versión y tiempo de inferencia. La referencia aparece por separado y una comparación indica si coinciden. La explicación relaciona la mano canónica, la posición y el rango de la política. La comparación entre situaciones permite observar cómo cambia la predicción con la misma mano. No se presenta como una explicación causal completa de la red.')
p('El dashboard recupera historial, distribución de acciones, concordancia y eventos procesados del usuario autenticado. El contador de eventos permite observar el flujo asíncrono y su eventual actualización. Cada análisis devuelve identificadores de solicitud, análisis y evento para rastrear el recorrido.')
table(['Ejemplo de demostración','Entrada','Salida real verificada'],[['Retirarse','UTG, 7s 2h, sin acciones previas','Fold'],['Subir','BTN, As Kh, folds UTG/HJ/CO','Raise a 2,5 BB'],['Pagar','BB contra BTN, 9s 9h','Call de 1,5 BB']], [4.7,7.5,5.2])
p('Si SageMaker falla o excede el timeout, la API responde 503 y la interfaz muestra el error. No sustituye silenciosamente la inferencia por una consulta al JSON. Los estados de carga, reinicio y validación ayudan a explicar la demostración a una audiencia sin conocimientos previos de póker.')

page('6 Contrato REST y comunicación distribuida')
figure(diagram('secuencia'),'Figura 4. Secuencia de una solicitud. La respuesta no espera a que el worker termine las estadísticas.')
table(['Método y ruta','Contrato'],[['POST /v1/auth/token','Formulario OAuth2. Devuelve JWT de 30 minutos.'],['GET /v1/catalog','Condiciones, seis escenarios y secuencias admitidas.'],['POST /v1/analyses','Cartas, escenario y acciones. 201 con inferencia real y referencia.'],['GET /v1/analyses/{id}','Análisis del usuario autenticado. 404 si no es suyo.'],['GET /v1/comparison','Seis predicciones para la misma mano.'],['GET /v1/dashboard','Historial y estadísticas del usuario.'],['GET /docs y /openapi.json','Swagger interactivo y esquema REST.'],['GET /health/live y /health/ready','Proceso y disponibilidad de dependencias.']], [6.1,11.3])
p('Análisis y evento pendiente se guardan dentro de la misma transacción PostgreSQL. El publicador busca eventos sin publicar y usa publisher confirms en una cola durable. Solo marca publicado después de la confirmación del broker. Si el proceso cae entre publicar y confirmar la transacción, puede reenviar el mismo evento. Esa entrega al menos una vez es deliberada (Broadcom, s.f.).')
p('El consumidor utiliza event_id como clave única de procesamiento y confirma el mensaje después del commit. Una reentrega no incrementa dos veces las estadísticas. Se limita a tres intentos ante errores de procesamiento y se deriva el fallo a una cola durable de descarte. Las conexiones se restablecen tras fallos. Los tests prueban idempotencia y persistencia del outbox; la verificación cloud confirmó el consumo real de los tres ejercicios.')

page('7 Seguridad y operación')
h('Autenticación y autorización')
p('La cuenta demo se crea con una contraseña aleatoria privada. Argon2 almacena su hash. El JWT usa HS256 con secreto aleatorio, emisor y audiencia validados y expiración de 30 minutos. La API exige Bearer token en sus operaciones de negocio y filtra cada análisis por usuario. No existe un endpoint público para registrar usuarios ni cambiar contraseñas. El token del cliente se conserva en sessionStorage y se elimina al cerrar sesión.')
h('Transporte y límites')
p('Nginx termina TLS 1.2/1.3 con certificado público de Let’s Encrypt para la IPv4. Un timer de systemd intenta renovar cada seis horas y recarga Nginx después de la renovación. HTTP redirige a HTTPS salvo el desafío ACME. La cuenta permite 120 solicitudes por minuto, el login limita intentos por IP y Nginx añade un límite específico al acceso. El cuerpo máximo HTTP es 32 KiB.')
p('PostgreSQL y RabbitMQ comunican por la red Docker privada del mismo host, sin puertos públicos. Ese tramo interno no usa TLS y su alcance se declara como limitación de la demo. El enlace FastAPI–SageMaker sí usa HTTPS y firmas IAM. Se exige IMDSv2 en EC2. En producción se requieren secretos administrados y permisos IAM mínimos en lugar del rol general del laboratorio.')
h('Observabilidad y recuperación')
p('CloudWatch recibe logs JSON de API, publicador y worker y las métricas nativas de SageMaker. Los logs registran request_id, código HTTP, duración y event_id, sin cuerpos, contraseñas ni tokens. /health/live distingue proceso vivo y /health/ready comprueba base de datos, broker y endpoint. Los contenedores tienen reinicio automático y los volúmenes conservan datos. Un reinicio controlado de API, publicador y worker conservó el historial y volvió a aprobar los 22 controles HTTP cloud.')
p('El repositorio contiene Dockerfile de aplicación e inferencia, compose.yaml y scripts de despliegue, pruebas y recolección de evidencia. No incluye .env, archivos de acceso, llaves, volúmenes ni credenciales AWS. La separación APP_ENV=production rechaza SQLite, modelo local y eventos locales, evitando que una demo parezca cloud sin usar los servicios exigidos.')
table(['Incidente','Comportamiento previsto'],[['SageMaker indisponible','503 explícito, sin análisis inventado.'],['Evento repetido','La clave event_id impide doble cómputo.'],['Worker reiniciado','Reconecta y consume pendientes persistidos.'],['Solicitud ajena o sin sesión','404 por propiedad o 401 sin token.'],['Límite excedido','429, manteniendo la política de seguridad.']], [6,11.4])

page('8 Pruebas funcionales e integración')
p('La batería local ejecutó 26 pruebas con pytest y el modelo entrenado real. El reporte artifacts/tests-local.xml conserva el resultado. La verificación HTTP dentro del despliegue ejecutó 22 controles adicionales contra FastAPI, SageMaker y RabbitMQ reales. Se distinguen las pruebas locales de contrato y los controles cloud; ninguna llamada fallida se presenta como un éxito.')
table(['Caso','Entrada y resultado esperado','Resultado'],[
['1 Datos','169 clases únicas, seis escenarios, sin solapamiento entre particiones.','Local OK'],
['2 Notación','77+, ATs+, 22–99 e intervalos suited expandidos correctamente.','Local OK'],
['3 Cartas','As/As rechaza con 422. As/Kh normaliza AKo.','Local y AWS OK'],
['4 Bote','BB contra BTN: bote 4 BB y call 1,5 BB.','Local OK'],
['5 Secuencia','Acciones incompletas o fuera de turno rechazan con 422.','Local y AWS OK'],
['6 Catálogo','Solo las seis situaciones declaradas. BB sin apertura no admitido.','Local y AWS OK'],
['7 Acceso','Sin token y contraseña incorrecta devuelven 401.','Local y AWS OK'],
['8 Aislamiento','Otro usuario no recupera el análisis y recibe 404.','Local OK'],
['9 Inferencia fold','UTG con 7s/2h devuelve fold desde SageMaker.','AWS OK'],
['10 Inferencia raise','BTN con As/Kh devuelve raise desde SageMaker.','AWS OK'],
['11 Inferencia call','BB contra BTN con 9s/9h devuelve call desde SageMaker.','AWS OK'],
['12 Persistencia','GET por id conserva request_id y versión del POST.','Local y AWS OK'],
['13 Error de modelo','Proveedor fallido devuelve 503 y no inserta recomendación.','Local OK'],
['14 Seguridad','Exceso por usuario devuelve 429.','Local OK'],
['15 Eventos','Outbox persistido, reentrega sin duplicación y consumo real.','Local y AWS OK'],
['16 Interoperabilidad','OpenAPI, catálogo, comparación y dashboard responden.','Local y AWS OK']], [2.7,11.8,2.9])
p('Los controles cloud confirmaron 3 eventos procesados para 3 análisis de demostración y la versión preflop-5b0e112653. Los escenarios de fallo se prueban mediante inyección controlada de errores en el proveedor local. No se interrumpió un endpoint ni se modificó otro proyecto para provocar fallos. La prueba de carga y sus límites se describen en la página siguiente.')

page('9 Rendimiento escalabilidad y costos')
p('Locust ejecutó cinco usuarios concurrentes durante cinco minutos con espera de 0,8–1,2 s. Cada uno empleó una cuenta sintética independiente para respetar 120 solicitudes/minuto por usuario. Las tareas distribuyen cinco análisis por cada consulta de dashboard. El generador se ejecutó en la EC2 contra localhost:8000: mide backend más SageMaker y persistencia, pero excluye Internet, Nginx/TLS y el navegador.')
table(['Métrica agregada de carga AWS','Medición'],[
['Solicitudes / fallos',f"{LOAD['Request Count']} / {LOAD['Failure Count']}"],
['Throughput',f"{float(LOAD['Requests/s']):.3f} solicitudes/s"],
['Latencia p50 / p95 / p99',f"{LOAD['50%']} / {LOAD['95%']} / {LOAD['99%']} ms"],
['Tasa de errores',f"{100*int(LOAD['Failure Count'])/max(1,int(LOAD['Request Count'])):.3f} %"]], [10,7.4])
acts=CLOUD.get('scaling_activities',[])
success=[a for a in acts if a.get('StatusCode')=='Successful']
p('El escalado administrado configura mínimo 1, máximo 2 y objetivo de 60 invocaciones por instancia y minuto, con cooldown de 60 s. '+('CloudWatch y el historial de escalado registraron al menos una actividad exitosa. El archivo cloud-metrics.json conserva capacidad, causa y tiempos reales.' if success else 'La captura final no registra una actividad de escalado finalizada con éxito. Esto acredita la política configurada y la carga ejecutada, pero no demuestra por sí solo un cambio de capacidad exitoso. El archivo cloud-metrics.json conserva el comportamiento observado.'))
h('Optimización medida')
p('Un microbenchmark local de 100 ejecuciones comparó cargar pesos por petición con mantener el modelo precargado, usando la misma mano AKo desde BTN. La media bajó de 1,348 ms a 0,086 ms, equivalente a 15,67 veces. El p95 bajó de 1,494 ms a 0,098 ms. SageMaker reutiliza el modelo al iniciar el contenedor. La medición es CPU local y no representa una mejora demostrada en latencia de red cloud.')
h('Presupuesto operativo')
p('La tarifa verificada para ml.m5.large de hosting en us-east-1 es USD 0,115/h y EC2 t3.medium USD 0,0418/h, sin asumir Free Tier (Amazon Web Services, s.f.-a, s.f.-b). La reserva de 8 h EC2, 10 horas-instancia ML, IPv4, almacenamiento y servicios menores suma aproximadamente USD 2,58, antes de contingencia y de posibles impuestos. El objetivo máximo es USD 5. No es una factura ni un límite automático de AWS.')
p('Un endpoint provisionado cobra mientras existe, aunque no reciba consultas. Detener EC2 conserva cargos de EBS e IPv4 y no detiene SageMaker. Mantener todo activo durante el fin de semana excedería el presupuesto. La operación exige ventanas acotadas y una retirada o pausa autorizada exclusivamente de recursos EP3, preservando datos y los proyectos ajenos. La aplicación de una sola EC2 no ofrece alta disponibilidad.')

page('10 Entrega accesos y referencias')
h('Reproducción y demostración')
p('README explica instalación local, entrenamiento, tests, AWS y operación. La defensa muestra login, cartas y secuencia, inferencia real con versión, consulta REST y actualización del dashboard. Los ejemplos UTG 72o, BTN AKo y BB 99 producen fold, raise y call. El endpoint ML permanece privado mediante IAM; la URL REST pública requiere sesión. Las credenciales demo no se incluyen en PDF, diapositivas ni GitHub.')
p('El repositorio y la carpeta output/entrega reúnen informe, presentación y guía de defensa. artifacts conserva métricas ML, prueba local, optimización y resultados cloud. La cuenta AWS Academy puede limitar disponibilidad por duración de la sesión. La fecha y hora oficiales de AVA y el acceso durante revisión deben verificarse con el docente. La modalidad individual y el cambio de tema siguen lo informado por el estudiante.')
h('Limitaciones y evolución')
p('El catálogo cerrado facilita explicar y validar el recorrido. Ampliarlo requiere definir nuevos datos y secuencias, entrenar y reevaluar el modelo. Para una academia real se necesita validar los rangos con especialistas, medir resultados educativos, obtener consentimiento para datos reales, gestionar roles y usuarios, reforzar IAM, cifrar los enlaces internos y distribuir la infraestructura. Ninguna de esas extensiones se presenta como implementada.')
h('Referencias')
refs=[
('Amazon Web Services. (s.f.-a). ','Amazon EC2 T3 instances.',' Recuperado el 20 de noviembre de 2026, de https://aws.amazon.com/ec2/instance-types/t3/'),
('Amazon Web Services. (s.f.-b). ','Amazon SageMaker AI pricing.',' Recuperado el 20 de noviembre de 2026, de https://aws.amazon.com/sagemaker/ai/pricing/'),
('Amazon Web Services. (s.f.-c). ','Deploy models for inference.',' Amazon SageMaker AI Developer Guide. https://docs.aws.amazon.com/sagemaker/latest/dg/deploy-model.html'),
('Broadcom. (s.f.). ','Consumer acknowledgements and publisher confirms.',' RabbitMQ documentation. https://www.rabbitmq.com/docs/confirms'),
('Duoc UC. (2025). ','Evaluación Parcial 3 Proyecto Integral de Despliegue y Optimización de Sistema IA Empresarial.',' [Pauta de ITY1102]. Material de asignatura.')
]
for author,title,tail in refs:
    para=p('');para.paragraph_format.left_indent=Cm(.5);para.paragraph_format.first_line_indent=Cm(-.5)
    para.add_run(author);para.add_run(title).italic=True;para.add_run(tail)
h('Declaración de uso de IA')
p('Se utilizó Codex de OpenAI para apoyar el diseño, generar y revisar código, ejecutar pruebas y preparar documentación y diapositivas. La asistencia se contrastó con la pauta y con resultados ejecutados. Los datos son sintéticos propios y las salidas del modelo se distinguen de la referencia. El estudiante debe revisar el contenido, comprender las decisiones y responder por la entrega académica.')
for para in doc.paragraphs:
    for border in list(para._p.iter(qn('w:pBdr'))):border.getparent().remove(border)
doc.save(OUT/'EP3_EquipoIndividual_Hueichapan.docx')
print(str(OUT/'EP3_EquipoIndividual_Hueichapan.docx'))
