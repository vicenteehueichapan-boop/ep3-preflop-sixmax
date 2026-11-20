"""Contenedor de inferencia SageMaker: /ping y /invocations."""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.model import Predictor
from app.policy import all_hands, policy

model = Predictor(Path(os.getenv("MODEL_DIR", "/opt/ml/model")))
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


class Input(BaseModel):
    scenario: str
    hand: str


@app.get('/ping')
def ping():
    return {'status':'ok','version':model.metadata['version']}


@app.post('/invocations')
def invoke(data: Input):
    if data.scenario not in policy()['scenarios'] or data.hand not in all_hands():
        raise HTTPException(422,'Situacion no soportada')
    return model.predict(data.scenario,data.hand)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8080, log_level='info')
