"""Paquete académico basado en whitelist. Excluye secretos, runtime y proyectos ajenos."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root=Path(__file__).resolve().parents[1]
out=root/'output/entrega'
entries=json.loads(subprocess.check_output([sys.executable,str(root/'scripts/export_source.py')],text=True,encoding='utf-8'))
pdfs=['EP3_EquipoIndividual_Hueichapan.pdf','EP3_Presentacion_EquipoIndividual.pdf']
for name in pdfs:
    if not (out/name).is_file():raise FileNotFoundError(name)
guide='''ENTREGA EP3 PREFLOP SIX MAX

1. EP3_EquipoIndividual_Hueichapan.pdf: informe técnico de 10 páginas.
2. EP3_Presentacion_EquipoIndividual.pdf: presentación de 6 láminas.
3. EP3_EquipoIndividual_Hueichapan.docx: copia editable del informe.
4. codigo/: aplicación, datos, modelo, infraestructura, pruebas y evidencias.
5. codigo/docs/DEFENSA.md: guion de 11 minutos y preguntas para ensayar.
6. codigo/docs/CUMPLIMIENTO.md: matriz de los 13 indicadores de la rúbrica.
7. codigo/docs/EP3_Postman.collection.json: colección sin contraseñas ni tokens.

Demo: https://54.162.150.183/
API: https://54.162.150.183/docs
GitHub: https://github.com/vicenteehueichapan-boop/ep3-preflop-sixmax

La URL exige laboratorio activo, EC2 iniciada y endpoint SageMaker disponible.
El endpoint ML es privado por IAM y no admite una llamada anónima desde navegador.
Las credenciales de acceso se entregan por separado en privado. Este ZIP no las contiene.
No se incluyeron .env, llaves, entornos virtuales, node_modules, datos runtime ni proyectos ajenos.

Métricas: 26 tests locales, 22 controles cloud; Locust 1464 solicitudes, 0 fallos,
4,89 solicitudes/s y p50/p95/p99 20/35/110 ms desde EC2. Modelo accuracy 94,87 %, macroF1 0,898.
Política propia didáctica. No es GTO ni una garantía de ganancia.

SageMaker cobra mientras existe el endpoint, aunque no haya consultas. Mantenerlo activo todo
el fin de semana excede el objetivo USD5. La pausa requiere autorización expresa sobre los
recursos EP3. No tocar otros proyectos. Confirmar ventanas de revisión y defensa con el docente.

La presentación PDF conserva las imágenes verificadas de las seis láminas. El deck editable
permanece en Spaces. El informe DOCX puede editarse en Word, pero cambiarlo exige comprobar
de nuevo que el PDF conserve diez páginas. Revisar y ensayar antes de entregar en AVA.
'''
(out/'LEEME_ENTREGA.txt').write_text(guide,encoding='utf-8')
zip_path=out/'EP3_Entrega_PreflopSixMax_Hueichapan.zip'
with ZipFile(zip_path,'w',ZIP_DEFLATED) as z:
    for entry in entries:
        name=entry['path']
        if any(part in {'.env','runtime','node_modules','.venv'} for part in Path(name).parts):raise RuntimeError('Ruta no publicable')
        z.writestr('codigo/'+name,entry['content'].encode('utf-8'))
    for name in pdfs+['EP3_EquipoIndividual_Hueichapan.docx','LEEME_ENTREGA.txt']:
        z.write(out/name,name)
    for name in ['aws-login.png','aws-sagemaker.png','mesa-local.png']:
        path=root/'output/playwright'/name
        if path.is_file():z.write(path,'codigo/output/playwright/'+name)
report={'zip':zip_path.name,'sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),'source_files':len(entries),'private_files_included':False}
(out/'MANIFEST_ENTREGA.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
