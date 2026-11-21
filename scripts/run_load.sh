#!/bin/bash
# Ejecutar solo en la NUEVA instancia EP3, contra su API propia.
set -euo pipefail
cd /opt/ep3-preflop/source
mkdir -p runtime/evidence
docker build -f Dockerfile.load -t ep3-preflop-load:1 .
docker run --rm --network host -v "$PWD/runtime/evidence:/evidence" ep3-preflop-load:1 \
 --host https://54.162.150.183 --headless --users 5 --spawn-rate 1 --run-time 5m \
 --csv /evidence/load-cloud --html /evidence/load-cloud.html --only-summary
