#!/bin/bash
# Ejecutar solo en la NUEVA instancia EP3, contra su API propia.
set -euo pipefail
cd /opt/ep3-preflop/source
mkdir -p runtime/evidence
docker build -f Dockerfile.load -t ep3-preflop-load:1 .
docker compose exec -T api python scripts/seed_load.py
docker run --rm --network host --env-file .env -e LOAD_USER_PREFIX=ep3-load -v "$PWD/runtime/evidence:/evidence" ep3-preflop-load:1 \
 --host http://127.0.0.1:8000 --headless --users 5 --spawn-rate 1 --run-time 5m \
 --csv /evidence/load-cloud --html /evidence/load-cloud.html --only-summary
