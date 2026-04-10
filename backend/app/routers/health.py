from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from ..database import get_db
from ..models import Event, Alert, Case
from ..config import settings

router = APIRouter(tags=["System"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/v1/stats", dependencies=[])
async def stats(db: AsyncSession = Depends(get_db)):
    """Общая статистика для дашборда (без auth для демо)"""
    cutoff = datetime.utcnow() - timedelta(hours=24)

    events_24h = (await db.execute(
        select(func.count(Event.id)).where(Event.created_at >= cutoff)
    )).scalar() or 0

    alerts_24h = (await db.execute(
        select(func.count(Alert.id)).where(Alert.created_at >= cutoff)
    )).scalar() or 0

    open_cases = (await db.execute(
        select(func.count(Case.id)).where(Case.status == "open")
    )).scalar() or 0

    critical = (await db.execute(
        select(func.count(Alert.id)).where(
            Alert.risk_level == "critical", Alert.created_at >= cutoff
        )
    )).scalar() or 0

    high = (await db.execute(
        select(func.count(Alert.id)).where(
            Alert.risk_level == "high", Alert.created_at >= cutoff
        )
    )).scalar() or 0

    medium = (await db.execute(
        select(func.count(Alert.id)).where(
            Alert.risk_level == "medium", Alert.created_at >= cutoff
        )
    )).scalar() or 0

    return {
        "total_events_24h": events_24h,
        "total_alerts_24h": alerts_24h,
        "open_cases": open_cases,
        "critical_alerts": critical,
        "high_alerts": high,
        "medium_alerts": medium,
    }
