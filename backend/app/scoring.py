"""
FMCWS Scoring Engine
====================
Реализует детерминированную систему скоринга риска мошенничества.

Архитектура:
- DEFAULT_RULES: встроенные правила (всегда активны при старте)
- ScoringEngine: загружает правила из БД, применяет к событию + истории сессии
- Результат: score [0–100], risk_level, triggered_rules, warning_message
"""
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from .models import Event, Rule
from .config import settings


# ─── Уровни риска ─────────────────────────────────────────────────────────────

RISK_LEVELS = [
    (settings.WARN_THRESHOLD_CRITICAL, "critical"),
    (settings.WARN_THRESHOLD_HIGH,     "high"),
    (settings.WARN_THRESHOLD_MEDIUM,   "medium"),
    (0,                                "low"),
]

WARNING_MESSAGES = {
    "low":      None,
    "medium":   (
        "⚠️ Обнаружена необычная активность в вашем аккаунте. "
        "Если это не вы — немедленно свяжитесь с банком."
    ),
    "high":     (
        "🔶 Выявлены признаки подозрительной активности. "
        "Рекомендуем прервать операцию и позвонить на горячую линию банка."
    ),
    "critical": (
        "🚨 ВНИМАНИЕ: Зафиксированы критические признаки мошенничества. "
        "Немедленно позвоните в банк и НЕ совершайте никаких операций!"
    ),
}

RECOMMENDATIONS = {
    "low":      "allow",
    "medium":   "step_up",
    "high":     "manual_review",
    "critical": "block",
}


# ─── Встроенные правила (seed) ─────────────────────────────────────────────────

DEFAULT_RULES = [
    {
        "code":        "LOGIN_NEW_DEVICE",
        "name":        "Вход с нового устройства",
        "description": "Клиент авторизовался с неизвестного ранее устройства",
        "event_type":  "LOGIN_SUCCESS",
        "score_delta": 30,
        "priority":    80,
    },
    {
        "code":        "LOGIN_FAIL_MULTIPLE",
        "name":        "Множественные неудачные входы",
        "description": "3 и более неуспешных попыток входа подряд",
        "event_type":  "LOGIN_FAIL",
        "score_delta": 25,
        "priority":    80,
    },
    {
        "code":        "NEW_RECIPIENT_TRANSFER",
        "name":        "Новый получатель + перевод",
        "description": "Добавление нового получателя и немедленный перевод в той же сессии",
        "event_type":  "TRANSFER_CONFIRM",
        "score_delta": 40,
        "priority":    90,
    },
    {
        "code":        "CONTACT_CHANGE_BEFORE_TRANSFER",
        "name":        "Смена контактных данных перед переводом",
        "description": "Смена телефона/e-mail в сессии, за которой следует перевод",
        "event_type":  "TRANSFER_CONFIRM",
        "score_delta": 35,
        "priority":    90,
    },
    {
        "code":        "ATYPICAL_TIME",
        "name":        "Нетипичное время активности",
        "description": "Любое действие клиента в период 00:00–05:59",
        "event_type":  "*",
        "score_delta": 20,
        "priority":    50,
    },
    {
        "code":        "PARALLEL_SESSION",
        "name":        "Параллельные сессии",
        "description": "Обнаружена активная сессия клиента с другого IP/устройства",
        "event_type":  "PARALLEL_SESSION_DETECTED",
        "score_delta": 30,
        "priority":    70,
    },
    {
        "code":        "IP_CHANGE_IN_SESSION",
        "name":        "Смена IP внутри сессии",
        "description": "IP-адрес изменился в рамках одной сессии",
        "event_type":  "IP_CHANGE",
        "score_delta": 15,
        "priority":    60,
    },
    {
        "code":        "LIMIT_CHANGE",
        "name":        "Изменение лимитов",
        "description": "Клиент изменил платёжные лимиты",
        "event_type":  "LIMIT_CHANGE",
        "score_delta": 25,
        "priority":    70,
    },
    {
        "code":        "CONTACT_CHANGE",
        "name":        "Смена контактных данных",
        "description": "Изменение номера телефона или e-mail",
        "event_type":  "CONTACT_CHANGE",
        "score_delta": 20,
        "priority":    70,
    },
    {
        "code":        "OTP_MULTIPLE_REQUESTS",
        "name":        "Множественные запросы OTP",
        "description": "3+ запросов OTP в течение 5 минут",
        "event_type":  "OTP_REQUEST",
        "score_delta": 20,
        "priority":    65,
    },
    {
        "code":        "NETWORK_CHANGE",
        "name":        "Смена сети/ASN",
        "description": "Изменение провайдера или ASN в рамках сессии",
        "event_type":  "NETWORK_CHANGE",
        "score_delta": 15,
        "priority":    55,
    },
    {
        "code":        "VIRTUAL_CARD_ISSUE",
        "name":        "Выпуск виртуальной карты",
        "description": "Запрос выпуска новой виртуальной карты",
        "event_type":  "VIRTUAL_CARD_ISSUE",
        "score_delta": 15,
        "priority":    50,
    },
    {
        "code":        "HIGH_AMOUNT_TRANSFER",
        "name":        "Перевод на крупную сумму",
        "description": "Сумма перевода превышает пороговое значение (extra.amount > 5000)",
        "event_type":  "TRANSFER_CREATE",
        "score_delta": 20,
        "priority":    60,
    },
    {
        "code":        "APP_VERSION_CHANGE",
        "name":        "Смена версии приложения",
        "description": "Клиент использует новую версию мобильного приложения",
        "event_type":  "APP_VERSION_CHANGE",
        "score_delta": 10,
        "priority":    40,
    },
]


# ─── Scoring Engine ────────────────────────────────────────────────────────────

@dataclass
class ScoringResult:
    score: float
    risk_level: str
    triggered_rules: list[str]
    warning_message: Optional[str]
    recommendation: str
    show_warning: bool


class ScoringEngine:
    """
    Применяет правила к событию + истории сессии за последние 30 минут.
    Возвращает ScoringResult.
    """

    async def score(
        self,
        event_data: dict,
        db: AsyncSession,
    ) -> ScoringResult:
        # Загружаем активные правила из БД
        rules_q = await db.execute(
            select(Rule).where(Rule.is_active == True).order_by(Rule.priority.desc())
        )
        db_rules = rules_q.scalars().all()

        # История сессии (последние 30 мин)
        session_history = await self._get_session_history(
            event_data["session_id"], event_data["client_id"], db
        )

        triggered: list[str] = []
        score: float = 0.0

        for rule in db_rules:
            delta = self._evaluate_rule(rule, event_data, session_history)
            if delta > 0:
                triggered.append(rule.code)
                score += delta

        # Clamp
        score = min(score, 100.0)

        # Risk level
        risk_level = "low"
        for threshold, level in RISK_LEVELS:
            if score >= threshold:
                risk_level = level
                break

        warning = WARNING_MESSAGES.get(risk_level)
        rec = RECOMMENDATIONS.get(risk_level, "allow")

        return ScoringResult(
            score=round(score, 2),
            risk_level=risk_level,
            triggered_rules=triggered,
            warning_message=warning,
            recommendation=rec,
            show_warning=risk_level in ("medium", "high", "critical"),
        )

    # ── Evaluate single rule ───────────────────────────────────────────────────

    def _evaluate_rule(
        self,
        rule: Rule,
        ev: dict,
        history: list[dict],
    ) -> float:
        code = rule.code
        etype = ev.get("event_type", "")
        extra = ev.get("extra") or {}

        # Wildcard event type (*) — проверяем доп. условие
        if rule.event_type != "*" and rule.event_type != etype:
            return 0.0

        match code:
            case "LOGIN_NEW_DEVICE":
                return rule.score_delta if extra.get("is_new_device") else 0.0

            case "LOGIN_FAIL_MULTIPLE":
                fail_count = sum(
                    1 for h in history if h["event_type"] == "LOGIN_FAIL"
                )
                return rule.score_delta if fail_count >= 2 else 0.0

            case "NEW_RECIPIENT_TRANSFER":
                has_new_recipient = any(
                    h["event_type"] == "RECIPIENT_ADD" for h in history
                )
                return rule.score_delta if has_new_recipient else 0.0

            case "CONTACT_CHANGE_BEFORE_TRANSFER":
                has_contact_change = any(
                    h["event_type"] == "CONTACT_CHANGE" for h in history
                )
                return rule.score_delta if has_contact_change else 0.0

            case "ATYPICAL_TIME":
                hour = datetime.utcnow().hour
                return rule.score_delta if hour < 6 else 0.0

            case "PARALLEL_SESSION":
                return rule.score_delta  # событие уже специфическое

            case "IP_CHANGE_IN_SESSION":
                prev_ips = {h["ip_address"] for h in history if h.get("ip_address")}
                cur_ip = ev.get("ip_address")
                return rule.score_delta if cur_ip and prev_ips and cur_ip not in prev_ips else 0.0

            case "LIMIT_CHANGE":
                return rule.score_delta

            case "CONTACT_CHANGE":
                return rule.score_delta

            case "OTP_MULTIPLE_REQUESTS":
                otp_count = sum(
                    1 for h in history if h["event_type"] == "OTP_REQUEST"
                )
                return rule.score_delta if otp_count >= 2 else 0.0

            case "NETWORK_CHANGE":
                prev_asns = {h["asn"] for h in history if h.get("asn")}
                cur_asn = ev.get("asn")
                return rule.score_delta if cur_asn and prev_asns and cur_asn not in prev_asns else 0.0

            case "VIRTUAL_CARD_ISSUE":
                return rule.score_delta

            case "HIGH_AMOUNT_TRANSFER":
                amount = extra.get("amount", 0)
                return rule.score_delta if float(amount) > 5000 else 0.0

            case "APP_VERSION_CHANGE":
                return rule.score_delta if extra.get("is_new_version") else 0.0

            case _:
                # Пользовательское правило: если event_type совпал — применяем дельту
                return rule.score_delta

    # ── Session history ────────────────────────────────────────────────────────

    async def _get_session_history(
        self,
        session_id: str,
        client_id: str,
        db: AsyncSession,
    ) -> list[dict]:
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        result = await db.execute(
            select(Event).where(
                and_(
                    Event.session_id == session_id,
                    Event.client_id == client_id,
                    Event.created_at >= cutoff,
                )
            ).order_by(Event.created_at.asc())
        )
        events = result.scalars().all()
        return [
            {
                "event_type": e.event_type,
                "ip_address": e.ip_address,
                "asn": e.asn,
                "extra": json.loads(e.extra) if e.extra else {},
            }
            for e in events
        ]


# Singleton
scoring_engine = ScoringEngine()


def classify_risk(score: float) -> str:
    for threshold, level in RISK_LEVELS:
        if score >= threshold:
            return level
    return "low"
