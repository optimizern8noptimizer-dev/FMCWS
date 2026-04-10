# FMCWS — Fraud Monitoring & Customer Warning Service
## Версия MVP 1.0.0

---

## Структура проекта

```
fmcws/
├── backend/                   # FastAPI backend (Python 3.12)
│   ├── app/
│   │   ├── main.py            # Точка входа, lifespan, CORS
│   │   ├── config.py          # Настройки (pydantic-settings)
│   │   ├── database.py        # SQLAlchemy async engine
│   │   ├── models.py          # ORM: Event, Alert, Case, Rule, AuditLog
│   │   ├── schemas.py         # Pydantic in/out схемы
│   │   ├── auth.py            # X-API-Key middleware
│   │   ├── scoring.py         # Скоринговый движок + 14 встроенных правил
│   │   └── routers/
│   │       ├── events.py      # POST /v1/events — приём и скоринг
│   │       ├── alerts.py      # GET/PATCH /v1/alerts
│   │       ├── cases.py       # GET/POST/PATCH /v1/cases
│   │       ├── rules.py       # CRUD /v1/rules
│   │       └── health.py      # GET /health, GET /v1/stats
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── web-sdk/
│   ├── fmcws-sdk.js           # Vanilla JS SDK (zero dependencies)
│   └── example.html           # Пример интеграции
│
├── admin-console/
│   └── index.html             # React SPA (CDN, без сборки)
│
├── mobile-sdk/
│   ├── android/
│   │   ├── FmcwsSDK.kt        # Kotlin SDK (OkHttp + Coroutines)
│   │   └── ExampleIntegration.kt
│   └── ios/
│       ├── FmcwsSDK.swift     # Swift SDK (URLSession + CryptoKit)
│       └── ExampleIntegration.swift
│
└── docker-compose.yml
```

---

## Быстрый старт

### Вариант 1 — Docker (рекомендуется)

```bash
cd fmcws
docker-compose up --build -d
```

Backend доступен: http://localhost:8000  
Swagger UI: http://localhost:8000/docs  
Admin Console: открыть `admin-console/index.html` в браузере

### Вариант 2 — локально (Python 3.12+)

```bash
cd fmcws/backend
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Конфигурация

Все параметры в `backend/.env`:

| Параметр | По умолчанию | Описание |
|---|---|---|
| `API_KEY` | demo-fmcws-api-key-change-in-prod | Ключ для X-API-Key header |
| `SECRET_KEY` | (сменить!) | JWT / шифрование |
| `DATABASE_URL` | sqlite+aiosqlite:///./fmcws.db | URL БД |
| `BANK_WEBHOOK_URL` | "" | Webhook банка для алертов |
| `WARN_THRESHOLD_MEDIUM` | 31 | Порог среднего риска |
| `WARN_THRESHOLD_HIGH` | 61 | Порог высокого риска |
| `WARN_THRESHOLD_CRITICAL` | 86 | Порог критического риска |

---

## API — ключевые эндпоинты

Все запросы требуют заголовок: `X-API-Key: <ваш_ключ>`

### Приём события
```http
POST /v1/events
Content-Type: application/json
X-API-Key: demo-fmcws-api-key-change-in-prod

{
  "session_id": "uuid-сессии",
  "client_id":  "псевдо-id-клиента",
  "event_type": "LOGIN_SUCCESS",
  "channel":    "web",
  "ip_address": "192.168.1.1",
  "extra": { "is_new_device": true }
}
```

**Ответ:**
```json
{
  "id": "event-uuid",
  "risk_score": 30.0,
  "risk_level": "medium",
  "triggered_rules": ["LOGIN_NEW_DEVICE"],
  "show_warning": true,
  "warning_message": "⚠️ Обнаружена необычная активность..."
}
```

### Тестирование (curl)
```bash
# Проверка работоспособности
curl http://localhost:8000/health

# Отправка тестового события
curl -X POST http://localhost:8000/v1/events \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-fmcws-api-key-change-in-prod" \
  -d '{
    "session_id": "test-session-001",
    "client_id":  "client-hash-001",
    "event_type": "LOGIN_SUCCESS",
    "channel":    "web",
    "ip_address": "192.168.1.1",
    "extra": {"is_new_device": true}
  }'

# Список алертов
curl http://localhost:8000/v1/alerts \
  -H "X-API-Key: demo-fmcws-api-key-change-in-prod"

# Статистика
curl http://localhost:8000/v1/stats
```

---

## Встроенные правила скоринга (14 шт.)

| Код | Событие | Δ Score | Описание |
|---|---|---|---|
| LOGIN_NEW_DEVICE | LOGIN_SUCCESS | +30 | Вход с нового устройства |
| LOGIN_FAIL_MULTIPLE | LOGIN_FAIL | +25 | 3+ неудачных входа подряд |
| NEW_RECIPIENT_TRANSFER | TRANSFER_CONFIRM | +40 | Новый получатель + перевод |
| CONTACT_CHANGE_BEFORE_TRANSFER | TRANSFER_CONFIRM | +35 | Смена контактов перед переводом |
| ATYPICAL_TIME | * | +20 | Активность 00:00–05:59 |
| PARALLEL_SESSION | PARALLEL_SESSION_DETECTED | +30 | Параллельные сессии |
| IP_CHANGE_IN_SESSION | IP_CHANGE | +15 | Смена IP в сессии |
| LIMIT_CHANGE | LIMIT_CHANGE | +25 | Изменение лимитов |
| CONTACT_CHANGE | CONTACT_CHANGE | +20 | Смена телефона/e-mail |
| OTP_MULTIPLE_REQUESTS | OTP_REQUEST | +20 | 3+ запросов OTP за 5 мин |
| NETWORK_CHANGE | NETWORK_CHANGE | +15 | Смена ASN/провайдера |
| VIRTUAL_CARD_ISSUE | VIRTUAL_CARD_ISSUE | +15 | Выпуск виртуальной карты |
| HIGH_AMOUNT_TRANSFER | TRANSFER_CREATE | +20 | Сумма > 5000 (extra.amount) |
| APP_VERSION_CHANGE | APP_VERSION_CHANGE | +10 | Новая версия приложения |

---

## Уровни риска

| Уровень | Score | Действие |
|---|---|---|
| 🟢 Низкий | 0–30 | Нет предупреждения, allow |
| 🟡 Средний | 31–60 | Предупреждение клиенту, step_up |
| 🟠 Высокий | 61–85 | Усиленное предупреждение, manual_review |
| 🔴 Критический | 86–100 | Критическое предупреждение, block |

---

## Admin Console

Открыть `admin-console/index.html` в браузере:
1. URL: `http://localhost:8000`
2. API Key: `demo-fmcws-api-key-change-in-prod`
3. Нажать «Подключиться»

Разделы: Дашборд · Алерты · Кейсы · События · Правила

---

## Web SDK — подключение

```html
<script src="fmcws-sdk.js"></script>
<script>
  var fmcws = new FMCWS({
    apiUrl:   'https://fmcws.bank.by',
    apiKey:   'YOUR_API_KEY',
    clientId: 'PSEUDONYMIZED_CLIENT_ID',
    debug:    false,
    autoTrack: true,
  });
  fmcws.init();
</script>
```

Автотрекинг форм через атрибуты:
```html
<form data-fmcws-event="TRANSFER_CONFIRM" data-fmcws-amount="1500">
  ...
</form>
```

---

## Mobile SDK — подключение

### Android
```kotlin
// Application.onCreate()
FmcwsSDK.init(this, FmcwsConfig(
    apiUrl   = "https://fmcws.bank.by",
    apiKey   = BuildConfig.FMCWS_API_KEY,
    clientId = "anonymous"
))

// Трекинг
FmcwsSDK.track("LOGIN_SUCCESS", mapOf("is_new_device" to true))

// Предупреждения
FmcwsSDK.setWarningListener(object : FmcwsWarningListener {
    override fun onWarning(warning: FmcwsWarning) { /* показать диалог */ }
})
```

### iOS
```swift
// AppDelegate / @main
FmcwsSDK.shared.initialize(config: FmcwsConfig(
    apiURL:   URL(string: "https://fmcws.bank.by")!,
    apiKey:   "YOUR_API_KEY",
    clientId: "anonymous"
))

// Трекинг
FmcwsSDK.shared.track("LOGIN_SUCCESS", extra: ["is_new_device": true])

// Предупреждения
FmcwsSDK.shared.warningDelegate = self  // реализовать FmcwsWarningDelegate
```

---

## Production checklist

- [ ] Сменить `API_KEY` и `SECRET_KEY` в `.env`
- [ ] Заменить SQLite на PostgreSQL (`DATABASE_URL=postgresql+asyncpg://...`)
- [ ] Установить `BANK_WEBHOOK_URL` для уведомлений банка
- [ ] Ограничить CORS origins в `main.py`
- [ ] Настроить TLS/HTTPS (nginx reverse proxy)
- [ ] Настроить ротацию логов
- [ ] Добавить мониторинг (Prometheus / Grafana)
- [ ] Провести нагрузочное тестирование
