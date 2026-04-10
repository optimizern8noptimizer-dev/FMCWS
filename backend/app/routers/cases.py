"""GET/POST/PATCH /v1/cases — управление кейсами"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import Case, AuditLog
from ..schemas import CaseCreate, CaseUpdate
from ..auth import require_api_key

router = APIRouter(prefix="/v1/cases", tags=["Cases"])


def _case_to_dict(c: Case) -> dict:
    return {
        "id": c.id,
        "case_number": c.case_number,
        "client_id": c.client_id,
        "alert_ids": json.loads(c.alert_ids) if c.alert_ids else [],
        "status": c.status,
        "priority": c.priority,
        "analyst_id": c.analyst_id,
        "notes": c.notes,
        "recommendation": c.recommendation,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


@router.post("", dependencies=[Depends(require_api_key)])
async def create_case(payload: CaseCreate, db: AsyncSession = Depends(get_db)):
    case = Case(
        client_id=payload.client_id,
        alert_ids=json.dumps(payload.alert_ids),
        priority=payload.priority,
        recommendation=payload.recommendation,
        notes=payload.notes,
    )
    db.add(case)
    audit = AuditLog(
        actor="system",
        action="case_created",
        resource_type="case",
        details=json.dumps({"client_id": payload.client_id, "priority": payload.priority}),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(case)
    return _case_to_dict(case)


@router.get("", dependencies=[Depends(require_api_key)])
async def list_cases(
    status: str | None = None,
    priority: str | None = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(Case).order_by(Case.created_at.desc()).limit(limit)
    if status:
        q = q.where(Case.status == status)
    if priority:
        q = q.where(Case.priority == priority)
    result = await db.execute(q)
    return [_case_to_dict(c) for c in result.scalars().all()]


@router.get("/{case_id}", dependencies=[Depends(require_api_key)])
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return _case_to_dict(case)


@router.patch("/{case_id}", dependencies=[Depends(require_api_key)])
async def update_case(
    case_id: str,
    payload: CaseUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(case, field, val)
    case.updated_at = datetime.utcnow()

    audit = AuditLog(
        actor=payload.analyst_id or "analyst",
        action="case_updated",
        resource_type="case",
        resource_id=case_id,
        details=json.dumps(payload.model_dump(exclude_none=True)),
    )
    db.add(audit)
    await db.commit()
    await db.refresh(case)
    return _case_to_dict(case)
