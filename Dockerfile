FROM node:24-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --ignore-scripts && npm rebuild esbuild
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS api
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/preflop
COPY requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt && useradd --uid 10001 --create-home app
COPY app ./app
COPY scripts/smoke_cloud.py ./scripts/smoke_cloud.py
COPY data/policy.json ./data/policy.json
COPY artifacts/metadata.json ./artifacts/metadata.json
COPY --from=web /web/dist ./frontend/dist
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health/live')"
CMD ["uvicorn","app.main:create_app","--factory","--host","0.0.0.0","--port","8000","--log-level","info"]

FROM python:3.12-slim AS inference
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1
WORKDIR /srv/preflop
RUN pip install --no-cache-dir torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir fastapi==0.165.0 uvicorn==0.54.0 && useradd --uid 10001 --create-home app
COPY app/__init__.py app/model.py app/policy.py app/serve.py ./app/
COPY data/policy.json ./data/policy.json
USER app
EXPOSE 8080
ENTRYPOINT ["python","-m","app.serve"]
