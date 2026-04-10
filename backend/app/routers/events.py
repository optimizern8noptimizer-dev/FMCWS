"""POST /v1/events — приём событий, скоринг, генерация алертов"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from ..database import get_db
from ..models import Event, Alert, AuditLog
from ..schemas import EventIn, EventOut
from ..auth import require_api_key
from ..scoring import scoring_engine
from ..config import settings

router = APIRouter(prefix="/v1/events", tags=["Events"])


@router.post("", response_model=EventOut, dependencies=[Depends(require_api_key)])
async def ingest_event(
    payload: EventIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Принимает событие из веб/мобильного канала или банковского backend.
    Запускает скоринговый движок, при превышении порога генерирует Alert.
    Возвращает результат скоринга + предупреждение для клиента (если нужно).
    """
    extra_json = json.dumps(payload.extra) if payload.extra else None

    # ── Создаём Event (без score — сначала нужна история) ──────────────────────
    event = Event(
        session_id=payload.session_id,
        client_id=payload.client_id,
        event_type=payload.event_type,
        channel=payload.channel,
        ip_address=payload.ip_address,
        device_fingerprint=payload.device_fingerprint,
        user_agent=payload.user_agent,
        asn=payload.asn,
        extra=extra_json,
    )
    db.add(event)
    await db.flush()  # получаем event.id, но не коммитим

    # ── Скоринг ────────────────────────────────────────────────────────────────
    result = await scoring_engine.score(payload.model_dump(), db)

    event.risk_score = result.score
    event.risk_level = result.risk_level
    event.triggered_rules = json.dumps(result.triggered_rules)

    # ── Генерируем Alert если уровень ≥ medium ─────────────────────────────────
    alert_created = None
    if result.risk_level in ("medium", "high", "critical"):
        alert = Alert(
            client_id=payload.client_id,
            session_id=payload.session_id,
            event_id=event.id,
            risk_score=result.score,
            risk_level=result.risk_level,
            triggered_rules=json.dumps(result.triggered_rules),
            recommendation=result.recommendation,
            client_warned=result.show_warning,
            warning_message=result.warning_message,
        )
        db.add(alert)
        alert_created = alert

    # ── Audit log ──────────────────────────────────────────────────────────────
    audit = AuditLog(
        actor="sdk",
        action="event_ingested",
        resource_type="event",
        resource_id=event.id,
        details=json.dumps({
            "event_type": payload.event_type,
            "risk_score": result.score,
            "risk_level": result.risk_level,
        }),
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(event)

    # ── Уведомление банка через webhook (fire-and-forget) ─────────────────────
    if alert_created and settings.BANK_WEBHOOK_URL:
        import asyncio
        asyncio.create_task(_notify_bank(alert_created, payload))

    return EventOut(
        id=event.id,
        session_id=event.session_id,
        client_id=event.client_id,
        event_type=event.event_type,
        channel=event.channel,
        risk_score=event.risk_score,
        risk_level=event.risk_level,
        triggered_rules=json.loads(event.triggered_rules) if event.triggered_rules else [],
        warning_message=result.warning_message,
        show_warning=result.show_warning,
        created_at=event.created_at,
    )


@router.get("", dependencies=[Depends(require_api_key)])
async def list_events(
    client_id: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Список последних событий (для аналитической консоли)"""
    q = select(Event).order_by(Event.created_at.desc()).limit(limit)
    if client_id:
        q = q.where(Event.client_id == client_id)
    if session_id:
        q = q.where(Event.session_id == session_id)
    result = await db.execute(q)
    events = result.scalars().all()
    return [
        {
            "id": e.id,
            "session_id": e.session_id,
            "client_id": e.client_id,
            "event_type": e.event_type,
            "channel": e.channel,
            "risk_score": e.risk_score,
            "risk_level": e.risk_level,
            "triggered_rules": json.loads(e.triggered_rules) if e.triggered_rules else [],
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]


async def _notify_bank(alert, payload: EventIn):
    """Отправка webhook-уведомления в банковский backend"""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(settings.BANK_WEBHOOK_URL, json={
                "alert_id": alert.id,
                "client_id": alert.client_id,
                "session_id": alert.session_id,
                "risk_score": alert.risk_score,
                "risk_level": alert.risk_level,
                "triggered_rules": json.loads(alert.triggered_rules),
                "recommendation": alert.recommendation,
                "timestamp": datetime.utcnow().isoformat(),
            })
    except Exception:
        pass  # Не блокируем основной поток
