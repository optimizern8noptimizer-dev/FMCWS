"""CRUD /v1/rules — управление правилами скоринга"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db
from ..models import Rule, AuditLog
from ..schemas import RuleCreate, RuleUpdate
from ..auth import require_api_key

router = APIRouter(prefix="/v1/rules", tags=["Rules"])


def _rule_to_dict(r: Rule) -> dict:
    return {
        "id": r.id,
        "code": r.code,
        "name": r.name,
        "description": r.description,
        "event_type": r.event_type,
        "score_delta": r.score_delta,
        "is_active": r.is_active,
        "priority": r.priority,
        "created_at": r.created_at.isoformat(),
    }


@router.get("", dependencies=[Depends(require_api_key)])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).order_by(Rule.priority.desc()))
    return [_rule_to_dict(r) for r in result.scalars().all()]


@router.post("", dependencies=[Depends(require_api_key)])
async def create_rule(payload: RuleCreate, db: AsyncSession = Depends(get_db)):
    # Проверяем уникальность code
    existing = await db.execute(select(Rule).where(Rule.code == payload.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Rule code '{payload.code}' already exists")
    rule = Rule(**payload.model_dump())
    db.add(rule)
    db.add(AuditLog(
        actor="admin",
        action="rule_created",
        resource_type="rule",
        details=json.dumps({"code": payload.code, "score_delta": payload.score_delta}),
    ))
    await db.commit()
    await db.refresh(rule)
    return _rule_to_dict(rule)


@router.patch("/{rule_id}", dependencies=[Depends(require_api_key)])
async def update_rule(
    rule_id: str,
    payload: RuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, val in payload.model_dump(exclude_none=True).items():
        setattr(rule, field, val)
    db.add(AuditLog(
        actor="admin",
        action="rule_updated",
        resource_type="rule",
        resource_id=rule_id,
        details=json.dumps(payload.model_dump(exclude_none=True)),
    ))
    await db.commit()
    await db.refresh(rule)
    return _rule_to_dict(rule)


@router.delete("/{rule_id}", dependencies=[Depends(require_api_key)])
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    db.add(AuditLog(
        actor="admin",
        action="rule_deleted",
        resource_type="rule",
        resource_id=rule_id,
    ))
    await db.commit()
    return {"deleted": rule_id}
