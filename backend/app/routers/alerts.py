"""GET/PATCH /v1/alerts — управление алертами"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import get_db
from ..models import Alert, AuditLog
from ..schemas import AlertOut, AlertUpdate
from ..auth import require_api_key

router = APIRouter(prefix="/v1/alerts", tags=["Alerts"])


def _alert_to_dict(a: Alert) -> dict:
    return {
        "id": a.id,
        "client_id": a.client_id,
        "session_id": a.session_id,
        "event_id": a.event_id,
        "risk_score": a.risk_score,
        "risk_level": a.risk_level,
        "triggered_rules": json.loads(a.triggered_rules) if a.triggered_rules else [],
        "status": a.status,
        "recommendation": a.recommendation,
        "bank_notified": a.bank_notified,
        "client_warned": a.client_warned,
        "warning_message": a.warning_message,
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat(),
    }


@router.get("", dependencies=[Depends(require_api_key)])
async def list_alerts(
    status: str | None = None,
    risk_level: str | None = None,
    client_id: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if status:
        q = q.where(Alert.status == status)
    if risk_level:
        q = q.where(Alert.risk_level == risk_level)
    if client_id:
        q = q.where(Alert.client_id == client_id)
    result = await db.execute(q)
    return [_alert_to_dict(a) for a in result.scalars().all()]


@router.get("/{alert_id}", dependencies=[Depends(require_api_key)])
async def get_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return _alert_to_dict(alert)


@router.patch("/{alert_id}", dependencies=[Depends(require_api_key)])
async def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if payload.status is not None:
        alert.status = payload.status
    if payload.recommendation is not None:
        alert.recommendation = payload.recommendation
    alert.updated_at = datetime.utcnow()

    audit = AuditLog(
        actor=payload.analyst_id or "analyst",
        action="alert_updated",
        resource_type="alert",
        resource_id=alert_id,
        details=json.dumps(payload.model_dump(exclude_none=True)),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(alert)
    return _alert_to_dict(alert)


@router.get("/stats/summary", dependencies=[Depends(require_api_key)])
async def alert_stats(db: AsyncSession = Depends(get_db)):
    """Статистика алертов для дашборда"""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)

    total = await db.execute(
        select(func.count(Alert.id)).where(Alert.created_at >= cutoff)
    )
    by_level = {}
    for lvl in ("low", "medium", "high", "critical"):
        cnt = await db.execute(
            select(func.count(Alert.id)).where(
                Alert.risk_level == lvl, Alert.created_at >= cutoff
            )
        )
        by_level[lvl] = cnt.scalar() or 0

    open_cnt = await db.execute(
        select(func.count(Alert.id)).where(Alert.status == "new")
    )

    return {
        "total_24h": total.scalar() or 0,
        "by_level": by_level,
        "open": open_cnt.scalar() or 0,
    }
