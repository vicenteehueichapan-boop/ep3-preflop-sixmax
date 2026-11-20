# Preflop Six Max

Entrenador académico preflop para ITY1102 EP3. PyTorch, FastAPI, React, PostgreSQL, RabbitMQ y AWS SageMaker.

El modelo aproxima una política didáctica propia. No es un solver GTO ni estima probabilidades de ganar.

## Ejecutar localmente

Python 3.12 y Node 24. Crear un entorno virtual e instalar `requirements.txt` y PyTorch CPU 2.9.1 desde https://download.pytorch.org/whl/cpu.

```powershell
python scripts/setup_local.py
python scripts/train.py
cd frontend
npm ci
npm run build
cd ..
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8013
```

Abrir http://127.0.0.1:8013. Las credenciales se generan en `.env`, que no se publica. El modo local usa SQLite y procesamiento local de eventos, identificados en la interfaz. Producción exige PostgreSQL, RabbitMQ y SageMaker.

## Pruebas

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -q --junitxml=artifacts/tests-local.xml
```

Desactivar la carga automática de plugins evita que el plugin de Locust modifique el threading usado por TestClient. No desactiva las pruebas.

## AWS

`python infra/cloud.py preflight` comprueba acceso, cuotas y costos sin crear recursos. `create-server` crea recursos separados con etiquetas `Project=ep3-preflop`. `associate-ip` asocia únicamente la IP nueva a la instancia registrada. El bootstrap despliega los contenedores, el modelo y HTTPS.

El presupuesto objetivo es USD 5. No ejecutar con precios o disponibilidad sin revisar. El código de infraestructura no elimina recursos. Las otras instancias del laboratorio no deben modificarse.

La documentación final y las evidencias de cloud se incorporan después de verificar el despliegue real.
