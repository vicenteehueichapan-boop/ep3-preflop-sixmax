"""Exporta solo codigo y artefactos academicos publicables; nunca runtime o credenciales."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
folders=['app','data','scripts','infra','tests','frontend','artifacts']
files=[root/name for name in ['README.md','.gitignore','.dockerignore','Dockerfile','compose.yaml','requirements.txt','requirements-api.txt','pytest.ini','locustfile.py']]
for folder in folders:
    for p in (root/folder).rglob('*'):
        rel=p.relative_to(root).as_posix()
        if not p.is_file() or any(x in p.parts for x in ['node_modules','__pycache__','dist']):continue
        if p.suffix not in {'.py','.js','.jsx','.css','.html','.json','.yaml','.sh','.csv'}:continue
        if p.name.startswith(('state','preflight')):continue
        files.append(p)
entries=[]
for p in sorted(set(files)):
    entries.append({'path':p.relative_to(root).as_posix(),'mode':'100644','type':'blob','content':p.read_text(encoding='utf-8-sig')})
print(json.dumps(entries,ensure_ascii=True))
