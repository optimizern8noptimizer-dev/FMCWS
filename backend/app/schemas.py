from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


# ─── Events ──────────────────────────────────────────────────────────────────

class EventIn(BaseModel):
    session_id: str = Field(..., description="Идентификатор сессии клиента")
    client_id: str = Field(..., description="Псевдонимизированный ID клиента")
    event_type: str = Field(..., description="Тип события (LOGIN_SUCCESS, TRANSFER_CREATE, ...)")
    channel: str = Field(..., description="Канал: web | ios | android | backend")
    ip_address: Optional[str] = None
    device_fingerprint: Optional[str] = None
    user_agent: Optional[str] = None
    asn: Optional[str] = None
    extra: Optional[dict] = None


class EventOut(BaseModel):
    id: str
    session_id: str
    client_id: str
    event_type: str
    channel: str
    risk_score: Optional[float]
    risk_level: Optional[str]
    triggered_rules: Optional[list[str]]
    warning_message: Optional[str] = None
    show_warning: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Alerts ───────────────────────────────────────────────────────────────────

class AlertOut(BaseModel):
    id: str
    client_id: str
    session_id: str
    event_id: str
    risk_score: float
    risk_level: str
    triggered_rules: list[str]
    status: str
    recommendation: Optional[str]
    bank_notified: bool
    client_warned: bool
    warning_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertUpdate(BaseModel):
    status: Optional[str] = None
    recommendation: Optional[str] = None
    analyst_id: Optional[str] = None


# ─── Cases ────────────────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    client_id: str
    alert_ids: list[str]
    priority: str = "medium"
    recommendation: Optional[str] = None
    notes: Optional[str] = None


class CaseOut(BaseModel):
    id: str
    case_number: str
    client_id: str
    alert_ids: list[str]
    status: str
    priority: str
    analyst_id: Optional[str]
    notes: Optional[str]
    recommendation: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CaseUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    analyst_id: Optional[str] = None
    notes: Optional[str] = None
    recommendation: Optional[str] = None


# ─── Rules ────────────────────────────────────────────────────────────────────

class RuleCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    event_type: str
    score_delta: float
    is_active: bool = True
    priority: int = 50


class RuleOut(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str]
    event_type: str
    score_delta: float
    is_active: bool
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


class RuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    score_delta: Optional[float] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


# ─── Misc ─────────────────────────────────────────────────────────────────────

class StatsOut(BaseModel):
    total_events_24h: int
    total_alerts_24h: int
    open_cases: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
