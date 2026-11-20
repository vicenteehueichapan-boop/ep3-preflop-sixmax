from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    password_hash: Mapped[str] = mapped_column(Text)


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now)
    request_id: Mapped[str] = mapped_column(String(36), unique=True)
    scenario: Mapped[str] = mapped_column(String(32))
    hand: Mapped[str] = mapped_column(String(3))
    action: Mapped[str] = mapped_column(String(8))
    reference_action: Mapped[str] = mapped_column(String(8))
    model_version: Mapped[str] = mapped_column(String(64))
    latency_ms: Mapped[float] = mapped_column(Float)
    payload: Mapped[dict] = mapped_column(JSON)


class Outbox(Base):
    __tablename__ = "outbox"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), unique=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(80), index=True)
    analysis_id: Mapped[str] = mapped_column(String(36), unique=True)
    created_at: Mapped[str] = mapped_column(String(40), default=now)


def database(url):
    if url.startswith("sqlite"):
        Path("runtime").mkdir(exist_ok=True)
    engine = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def configure(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine, expire_on_commit=False)


def process_event(session, event_id):
    # Lock the outbox row before inserting the deduplication record (PostgreSQL).
    item = session.scalar(select(Outbox).where(Outbox.id == event_id).with_for_update())
    if item is None:
        raise ValueError("Evento desconocido")
    if item.processed or session.get(ProcessedEvent, event_id):
        return False
    analysis = session.get(Analysis, item.analysis_id)
    session.add(ProcessedEvent(id=event_id, user_id=analysis.user_id, analysis_id=analysis.id))
    item.processed = True
    item.last_error = None
    return True

