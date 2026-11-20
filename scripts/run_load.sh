#!/bin/bash
# Ejecutar solo en la NUEVA instancia EP3, contra su API propia.
set -euo pipefail
cd /opt/ep3-preflop/source
mkdir -p runtime/evidence
docker build -f Dockerfile.load -t ep3-preflop-load:1 .
docker run --rm --network host --env-file .env -v "$PWD/runtime/evidence:/evidence" ep3-preflop-load:1 \
 --host http://127.0.0.1:8000 --headless --users 10 --spawn-rate 2 --run-time 5m \
 --csv /evidence/load-cloud --html /evidence/load-cloud.html --only-summary
