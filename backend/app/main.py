"""
FMCWS — Fraud Monitoring & Customer Warning Service
Backend API (FastAPI + SQLite)

Запуск: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
Документация: http://localhost:8000/docs
"""
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .database import create_tables, async_session_maker
from .models import Rule
from .scoring import DEFAULT_RULES
from .config import settings
from .routers import events, alerts, cases, rules, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────────
    await create_tables()
    await _seed_rules()
    yield
    # ── Shutdown ───────────────────────────────────────────────────────────────


async def _seed_rules():
    """Загружает DEFAULT_RULES если таблица rules пуста"""
    async with async_session_maker() as db:
        existing = await db.execute(select(Rule))
        if existing.scalars().first():
            return
        for rule_data in DEFAULT_RULES:
            rule = Rule(
                code=rule_data["code"],
                name=rule_data["name"],
                description=rule_data.get("description"),
                event_type=rule_data["event_type"],
                score_delta=rule_data["score_delta"],
                priority=rule_data.get("priority", 50),
                is_active=True,
            )
            db.add(rule)
        await db.commit()
        print(f"[FMCWS] Seeded {len(DEFAULT_RULES)} default rules")


app = FastAPI(
    title="FMCWS — Fraud Monitoring & Customer Warning Service",
    description=(
        "API сервиса мониторинга признаков мошенничества "
        "в интернет- и мобильном банкинге (Республика Беларусь)"
    ),
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ── CORS (для Admin Console / Web SDK) ────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # В prod — ограничить доменами банка
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(events.router)
app.include_router(alerts.router)
app.include_router(cases.router)
app.include_router(rules.router)
