"""Exporta solo codigo y artefactos academicos publicables; nunca runtime o credenciales."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

root=Path(__file__).resolve().parents[1]
folders=['app','data','scripts','infra','tests','frontend','artifacts','docs']
files=[root/name for name in ['README.md','.gitignore','.dockerignore','Dockerfile','Dockerfile.load','compose.yaml','requirements.txt','requirements-api.txt','pytest.ini','locustfile.py']]
for folder in folders:
    for p in (root/folder).rglob('*'):
        rel=p.relative_to(root).as_posix()
        if not p.is_file() or any(x in p.parts for x in ['node_modules','__pycache__','dist']):continue
        if p.suffix not in {'.py','.js','.jsx','.css','.html','.json','.yaml','.sh','.csv','.md','.xml'}:continue
        if p.name.startswith(('state','preflight')):continue
        files.append(p)
entries=[]
for p in sorted(set(files)):
    rel=p.relative_to(root).as_posix()
    content=p.read_text(encoding='utf-8-sig')
    if rel=='artifacts/cloud-metrics.json':
        raw=json.loads(content)
        public={k:raw[k] for k in ['collected_at','region','status','created_at','metrics','load'] if k in raw}
        public['load_profile']={k:v for k,v in raw.get('load_profile',{}).items() if k!='host'}
        public['variants']=[{k:v[k] for k in ['CurrentInstanceCount','DesiredInstanceCount','CurrentWeight','DesiredWeight'] if k in v} for v in raw.get('variants',[])]
        public['scalable_targets']=[{k:v[k] for k in ['MinCapacity','MaxCapacity'] if k in v} for v in raw.get('scalable_targets',[])]
        public['scaling_activities']=[{k:v[k] for k in ['StatusCode','Description','StartTime','EndTime'] if k in v} for v in raw.get('scaling_activities',[])]
        public['log_groups']=[{k:v[k] for k in ['storedBytes','retentionInDays'] if k in v} for v in raw.get('log_groups',[])]
        public['publication_note']='Resumen de metricas. Se omiten cuenta AWS, roles, ARN, imagen ECR e identificadores de recursos.'
        content=json.dumps(public,indent=2,ensure_ascii=False)
        if re.search(r'arn:aws|(?<![\d.])\d{12}(?![\d.])|\bi-[a-f0-9]{8,}\b|\.dkr\.ecr',content):
            raise RuntimeError('Identificador interno inesperado en resumen publico')
    elif rel=='artifacts/tests-local.xml':
        tree=ET.fromstring(content)
        for node in tree.iter():
            if 'hostname' in node.attrib:node.set('hostname','test-host')
        content=ET.tostring(tree,encoding='unicode')
    entries.append({'path':rel,'mode':'100644','type':'blob','content':content})
print(json.dumps(entries,ensure_ascii=True))
