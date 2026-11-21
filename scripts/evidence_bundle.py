"""Exporta solo la lista cerrada de evidencias públicas. Nunca lee .env."""
import base64
import json
import zlib
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'runtime/evidence'
names=['cloud-smoke.json','cloud-metrics.json','recovery-check.json','recovery-before-readiness-fix.json','load-cloud_stats.csv','load-cloud_failures.csv']
files={name:(root/name).read_text(encoding='utf-8') for name in names if (root/name).exists()}
print('EP3_EVIDENCE_BEGIN')
print(base64.b64encode(zlib.compress(json.dumps(files).encode())).decode())
print('EP3_EVIDENCE_END')
