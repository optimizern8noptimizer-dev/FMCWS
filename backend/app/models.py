import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


def gen_case_number() -> str:
    import random
    return f"CASE-{datetime.utcnow().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    client_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(32))        # web | ios | android | backend
    ip_address: Mapped[str | None] = mapped_column(String(64))
    device_fingerprint: Mapped[str | None] = mapped_column(String(256))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    asn: Mapped[str | None] = mapped_column(String(64))
    extra: Mapped[str | None] = mapped_column(Text)         # JSON — доп. поля события
    risk_score: Mapped[float | None] = mapped_column(Float)
    risk_level: Mapped[str | None] = mapped_column(String(16))
    triggered_rules: Mapped[str | None] = mapped_column(Text)  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    client_id: Mapped[str] = mapped_column(String(36), index=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id"))
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))     # low | medium | high | critical
    triggered_rules: Mapped[str] = mapped_column(Text)      # JSON array of rule names
    status: Mapped[str] = mapped_column(String(32), default="new")
    # new | reviewing | resolved | false_positive
    recommendation: Mapped[str | None] = mapped_column(String(64))
    # step_up | manual_review | block | allow
    bank_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    client_warned: Mapped[bool] = mapped_column(Boolean, default=False)
    warning_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    case_number: Mapped[str] = mapped_column(String(32), unique=True, default=gen_case_number)
    client_id: Mapped[str] = mapped_column(String(36), index=True)
    alert_ids: Mapped[str] = mapped_column(Text)            # JSON array
    status: Mapped[str] = mapped_column(String(32), default="open")
    # open | investigating | closed_fraud | closed_legit
    priority: Mapped[str] = mapped_column(String(16), default="medium")  # low|medium|high|critical
    analyst_id: Mapped[str | None] = mapped_column(String(128))
    notes: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(64))
    score_delta: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=50)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    actor: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[str | None] = mapped_column(String(64))
    details: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
