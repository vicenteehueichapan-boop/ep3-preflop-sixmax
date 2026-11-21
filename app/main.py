import json
import logging
import threading
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyCookie, OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text

from app.config import Settings
from app.db import Analysis, Outbox, ProcessedEvent, User, database, process_event
from app.inference import InferenceUnavailable, LocalInference, SageMakerInference
from app.policy import ROOT, ACTIONS, expected_actions, policy, reference, state_for

log = logging.getLogger("preflop")
hasher = PasswordHasher()
oauth = OAuth2PasswordBearer(tokenUrl="/v1/auth/token", auto_error=False)


class ActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    position: str
    action: str
    raise_to_bb: float | None = None


class AnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: str
    cards: list[str] = Field(min_length=2, max_length=2)
    actions: list[ActionInput] = Field(max_length=5)


class SlidingRateLimit:
    def __init__(self):
        self.lock = threading.Lock()
        self.buckets = {}

    def check(self, key, limit):
        moment = time.monotonic()
        with self.lock:
            # Bound memory from abandoned login addresses / users.
            if len(self.buckets) > 2000:
                self.buckets = {k: q for k, q in self.buckets.items() if q and q[-1] > moment - 60}
            bucket = self.buckets.setdefault(key, deque())
            while bucket and bucket[0] <= moment - 60:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(429, "Demasiadas solicitudes. Espera un minuto.", headers={"Retry-After": "60"})
            bucket.append(moment)


def create_app(settings=None, predictor=None):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = settings or Settings.from_env()
    settings.validate()
    engine, sessions = database(settings.database_url)
    with sessions.begin() as session:
        if not session.get(User, settings.demo_username):
            session.add(User(id=settings.demo_username, password_hash=hasher.hash(settings.demo_password)))
    predictor = predictor or (LocalInference() if settings.model_backend == "local" else SageMakerInference(settings))
    limiter = SlidingRateLimit()
    @asynccontextmanager
    async def lifespan(_):
        yield
        engine.dispose()
    app = FastAPI(title="Preflop Six Max API", version="1.1.0", lifespan=lifespan,
        description="Entrenador de politica didactica. No GTO. Sesion invitada automatica, OAuth2 para clientes REST e historial aislado.")
    app.state.sessions, app.state.engine = sessions, engine
    app.state.predictor, app.state.settings = predictor, settings
    app.state.limiter = limiter

    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        started = time.perf_counter()
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        elapsed = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/v1/") else "no-cache"
        log.info(json.dumps({"request_id": request.state.request_id, "path": request.url.path, "status": response.status_code, "latency_ms": round(elapsed, 3)}))
        return response

    cookie_name = "__Host-preflop_demo" if settings.environment == "production" else "preflop_demo"
    cookie_auth = APIKeyCookie(name=cookie_name, auto_error=False)

    def same_origin(request):
        origin = request.headers.get("origin")
        if origin and (urlsplit(origin).netloc != request.headers.get("host") or urlsplit(origin).scheme not in {"http", "https"}):
            raise HTTPException(403, "Origen de solicitud no admitido.")
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, "Origen de solicitud no admitido.")

    def identity(token, guest_only=False):
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience="preflop", issuer="preflop-api", options={"require": ["exp", "sub", "iss", "aud"]})
            username = payload["sub"]
            if guest_only and (payload.get("kind") != "guest" or not username.startswith("guest-")):
                raise ValueError("Sesion no invitada")
            with sessions() as session:
                if not session.get(User, username):
                    raise ValueError("Usuario inexistente")
            return username
        except (jwt.PyJWTError, ValueError, KeyError) as exc:
            raise HTTPException(401, "Sesion invalida o vencida.", headers={"WWW-Authenticate": "Bearer"}) from exc

    def current_user(request: Request, token=Depends(oauth), cookie_token=Depends(cookie_auth)):
        if not token and not cookie_token:
            raise HTTPException(401, "Sesion requerida.", headers={"WWW-Authenticate": "Bearer"})
        if not token and request.method not in {"GET", "HEAD", "OPTIONS"}:
            same_origin(request)
        username = identity(token or cookie_token, guest_only=not bool(token))
        limiter.check("api:" + username, settings.rate_limit)
        return username

    @app.post("/v1/demo/session")
    def guest_session(request: Request):
        same_origin(request)
        limiter.check("guest-session:" + (request.client.host if request.client else "unknown"), 20)
        username = None
        existing = request.cookies.get(cookie_name)
        if existing:
            try:
                username = identity(existing, guest_only=True)
            except HTTPException:
                pass
        if not username:
            username = "guest-" + str(uuid.uuid4())
            with sessions.begin() as session:
                session.add(User(id=username, password_hash=app.state.dummy_hash))
        token = jwt.encode({"sub": username, "kind": "guest", "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "iss": "preflop-api", "aud": "preflop"}, settings.jwt_secret, algorithm="HS256")
        response = JSONResponse({"session_type": "guest", "expires_in": 1800})
        response.set_cookie(cookie_name, token, max_age=1800, httponly=True, secure=settings.environment == "production", samesite="strict", path="/")
        return response

    @app.post("/v1/auth/token")
    def login(request: Request, form: OAuth2PasswordRequestForm = Depends()):
        # X-Forwarded-For is not trusted; Nginx also applies an IP-based limit.
        limiter.check("login:" + (request.client.host if request.client else "unknown"), 20)
        with sessions() as session:
            user = session.get(User, form.username)
            try:
                valid = hasher.verify(user.password_hash if user else app.state.dummy_hash, form.password)
            except VerificationError:
                valid = False
            if not user or user.id.startswith("guest-") or not valid:
                raise HTTPException(401, "Usuario o clave incorrectos.", headers={"WWW-Authenticate": "Bearer"})
        expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jwt.encode({"sub": user.id, "exp": expiry, "iss": "preflop-api", "aud": "preflop"}, settings.jwt_secret, algorithm="HS256")
        return {"access_token": token, "token_type": "bearer", "expires_in": 1800}

    app.state.dummy_hash = hasher.hash(str(uuid.uuid4()))

    @app.get("/v1/catalog")
    def catalog(username=Depends(current_user)):
        return {"policy_version": policy()["version"], "game": policy()["game"],
            "scenarios": [{"id": s, **v, "actions": expected_actions(s)} for s, v in policy()["scenarios"].items()],
            "model_backend": settings.model_backend, "event_transport": settings.event_transport, "username": username}

    @app.post("/v1/analyses", status_code=201)
    def analyze(body: AnalysisInput, request: Request, username=Depends(current_user)):
        actions = [a.model_dump(exclude_none=True) for a in body.actions]
        try:
            state = state_for(body.scenario, body.cards, actions)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        started = time.perf_counter()
        try:
            result = app.state.predictor.predict(body.scenario, state["hand"])
        except InferenceUnavailable as exc:
            log.warning(json.dumps({"request_id": request.state.request_id, "error": "inference_unavailable"}))
            raise HTTPException(503, str(exc)) from exc
        elapsed = (time.perf_counter() - started) * 1000
        action = result["action"]
        if action not in state["legal_actions"]:
            raise HTTPException(503, "El modelo devolvio una accion no admitida.")
        ref = reference(body.scenario, state["hand"])
        item_id, event_id = str(uuid.uuid4()), str(uuid.uuid4())
        payload = {"id": item_id, "request_id": request.state.request_id, "event_id": event_id,
            "scenario": body.scenario, "cards": body.cards, "state": state, **result,
            "reference_action": ref, "matches_reference": action == ref,
            "policy_version": policy()["version"], "inference_ms": round(elapsed, 3),
            "source": settings.model_backend, "processing_mode": settings.event_transport,
            "raise_to_bb": state["raise_to_bb"] if action == "raise" else None,
            "explanation": {"hand": state["hand"], "position": state["hero"],
                "reference_rule": policy()["scenarios"][body.scenario]["raise" if ref == "raise" else "call"] if ref != "fold" else "Fuera de los rangos de raise y call de esta situacion.",
                "meaning": "La prediccion aproxima una politica didactica; las puntuaciones no son probabilidad de ganar."}}
        with sessions.begin() as session:
            session.add(Analysis(id=item_id, user_id=username, request_id=request.state.request_id,
                scenario=body.scenario, hand=state["hand"], action=action, reference_action=ref,
                model_version=result["model_version"], latency_ms=elapsed, payload=payload))
            session.flush()
            session.add(Outbox(id=event_id, analysis_id=item_id))
            session.flush()
            if settings.event_transport == "local":
                process_event(session, event_id)
                session.get(Outbox, event_id).published = True
        return payload

    @app.get("/v1/analyses/{analysis_id}")
    def get_analysis(analysis_id: str, username=Depends(current_user)):
        with sessions() as session:
            item = session.get(Analysis, analysis_id)
            if not item or item.user_id != username:
                raise HTTPException(404, "Analisis no encontrado.")
            return {**item.payload, "created_at": item.created_at}

    @app.get("/v1/comparison")
    def comparison(card1: str, card2: str, username=Depends(current_user)):
        from app.policy import canonical_cards
        try:
            hand = canonical_cards([card1, card2])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        try:
            return {"hand": hand, "comparisons": [{"scenario": s, "label": n["label"],
                **app.state.predictor.predict(s, hand), "reference_action": reference(s, hand)} for s, n in policy()["scenarios"].items()]}
        except InferenceUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.get("/v1/dashboard")
    def dashboard(username=Depends(current_user)):
        with sessions() as session:
            items = session.scalars(select(Analysis).where(Analysis.user_id == username).order_by(Analysis.created_at.desc()).limit(20)).all()
            distribution = dict(session.execute(select(Analysis.action, func.count()).where(Analysis.user_id == username).group_by(Analysis.action)).all())
            processed = session.scalar(select(func.count()).select_from(ProcessedEvent).where(ProcessedEvent.user_id == username))
            total = sum(distribution.values())
            matches = session.scalar(select(func.count()).select_from(Analysis).where(Analysis.user_id == username, Analysis.action == Analysis.reference_action))
            return {"total": total, "processed_events": processed, "distribution": distribution,
                "matches_reference": matches, "event_transport": settings.event_transport,
                "recent": [{**i.payload, "created_at": i.created_at} for i in items]}

    @app.get("/health/live")
    def live():
        return {"status": "alive", "environment": settings.environment}

    @app.get("/health/ready")
    def ready():
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            if settings.model_backend == "sagemaker":
                import boto3
                response = boto3.client("sagemaker", region_name=settings.aws_region).describe_endpoint(EndpointName=settings.endpoint_name)
                if response["EndpointStatus"] != "InService":
                    raise RuntimeError("Modelo no disponible")
            if settings.event_transport == "rabbitmq":
                import pika
                conn = pika.BlockingConnection(pika.URLParameters(settings.rabbit_url))
                conn.close()
            return {"status": "ready", "model_backend": settings.model_backend, "events": settings.event_transport}
        except Exception:
            return JSONResponse({"status": "not_ready"}, status_code=503)

    dist = ROOT / "frontend/dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app

