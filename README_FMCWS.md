<div align="center">

<img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/Docker-ready-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
<img src="https://img.shields.io/badge/Kotlin%20%7C%20Swift-Mobile_SDK-7F52FF?style=for-the-badge&logo=kotlin&logoColor=white"/>
<img src="https://img.shields.io/badge/SQLite%20%7C%20PostgreSQL-Database-003B57?style=for-the-badge&logo=postgresql&logoColor=white"/>

<br/><br/>

```
 ███████╗███╗   ███╗ ██████╗██╗    ██╗███████╗
 ██╔════╝████╗ ████║██╔════╝██║    ██║██╔════╝
 █████╗  ██╔████╔██║██║     ██║ █╗ ██║███████╗
 ██╔══╝  ██║╚██╔╝██║██║     ██║███╗██║╚════██║
 ██║     ██║ ╚═╝ ██║╚██████╗╚███╔███╔╝███████║
 ╚═╝     ╚═╝     ╚═╝ ╚═════╝ ╚══╝╚══╝ ╚══════╝

   FRAUD MONITORING & CUSTOMER WARNING SERVICE
```

# FMCWS

**Система мониторинга мошенничества и предупреждения клиентов**

Платформа для банков и финтех-компаний: скоринг поведенческих событий в реальном времени, автоматическое предупреждение клиентов, кейс-менеджмент и полный audit trail — с поддержкой Web, Android и iOS.

[🚀 Быстрый старт](#-быстрый-старт) · [📡 API Reference](#-api-reference) · [🛡 Правила скоринга](#-встроенные-правила-скоринга) · [📱 Mobile SDK](#-mobile-sdk) · [🌐 Web SDK](#-web-sdk)

---

</div>

## Содержание

- [Что это и зачем](#-что-это-и-зачем)
- [Архитектура](#-архитектура)
- [Возможности](#-возможности)
- [Быстрый старт](#-быстрый-старт)
- [Конфигурация](#-конфигурация)
- [API Reference](#-api-reference)
- [Встроенные правила скоринга](#-встроенные-правила-скоринга)
- [Уровни риска](#-уровни-риска)
- [Web SDK](#-web-sdk)
- [Mobile SDK](#-mobile-sdk)
- [Admin Console](#-admin-console)
- [Структура проекта](#-структура-проекта)
- [Production checklist](#-production-checklist)

---

## 🎯 Что это и зачем

Банки теряют миллиарды из-за социальной инженерии и компрометации аккаунтов. FMCWS решает ключевую задачу: **обнаружить аномалию и предупредить клиента до того, как транзакция прошла**.

```
Клиент выполняет действие
         │
         ▼
  Web / Mobile SDK      ──►  POST /v1/events
         │
         ▼
  ┌──────────────────────────────────────────┐
  │         Скоринговый движок               │
  │                                          │
  │  14 встроенных правил (расширяемых)      │
  │  Накопительный риск-скор (0–100)         │
  │  Определение уровня: LOW/MED/HIGH/CRIT   │
  └──────────────────────────────────────────┘
         │
         ├──► score ≤ 30   →  Allow (нет действий)
         ├──► score 31–60  →  Предупреждение клиенту + step_up
         ├──► score 61–85  →  Усиленное предупреждение + manual_review
         └──► score 86–100 →  Блокировка + webhook в банк
```

**Ключевые сценарии:**
- Вход с нового устройства после смены контактных данных
- Серия неудачных попыток входа перед крупным переводом
- Активность в нетипичное время + новый получатель перевода
- Параллельные сессии (признак компрометации аккаунта)

---

## 🏗 Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                        FMCWS Platform                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Web SDK    │  │ Android SDK  │  │    iOS SDK       │  │
│  │ (fmcws.js)  │  │ (Kotlin)     │  │ (Swift)          │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         └─────────────────┼──────────────────-─┘           │
│                           │  POST /v1/events               │
│                    ┌──────▼────────┐                        │
│                    │  FastAPI App  │                        │
│                    │               │                        │
│                    │  ┌──────────┐ │                        │
│                    │  │ scoring  │ │  ◄── 14 правил         │
│                    │  │ engine   │ │  ◄── кастомные правила │
│                    │  └──────────┘ │                        │
│                    │               │                        │
│                    │  ┌──────────┐ │                        │
│                    │  │ SQLite / │ │  Events / Alerts       │
│                    │  │Postgres  │ │  Cases / Rules         │
│                    │  └──────────┘ │  AuditLog              │
│                    └──────┬────────┘                        │
│                           │                                 │
│                    ┌──────▼────────┐                        │
│                    │ Admin Console │  React SPA (CDN)       │
│                    └───────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                           │
                     Webhook ──► Банковская АБС
```

---

## ⚡ Возможности

### 🔍 Скоринг в реальном времени
- Накопительный риск-скор 0–100 на основе поведенческих событий
- 14 встроенных правил, адаптированных под паттерны социальной инженерии
- Кастомные правила через API и Admin Console — без деплоя
- Учёт контекста: время суток, история устройств, цепочки событий

### ⚠️ Предупреждение клиентов
- Автоматические предупреждения в канале клиента (Web / Mobile)
- Настраиваемые пороги риска (конфигурация через `.env`)
- Локализованные сообщения с инструкциями для клиента
- Webhook-уведомления в банковскую АБС при критическом риске

### 📋 Кейс-менеджмент
- Автоматическое создание кейсов по алертам
- Статусы: `open` → `in_review` → `resolved` / `false_positive`
- Полный audit trail каждого изменения
- Приоритизация по уровню риска

### 🔌 Мультиплатформенная интеграция
- **Web SDK** — vanilla JS, zero dependencies, автотрекинг форм
- **Android SDK** — Kotlin + OkHttp + Coroutines
- **iOS SDK** — Swift + URLSession + CryptoKit
- **REST API** — любая платформа через HTTP

---

## 🚀 Быстрый старт

### Вариант 1 — Docker (рекомендуется)

```bash
# Клонировать репозиторий
git clone https://github.com/your-username/fmcws.git
cd fmcws

# Запустить
docker-compose up --build -d
```

| Сервис | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Admin Console | открыть `admin-console/index.html` |

### Вариант 2 — локально (Python 3.12+)

```bash
cd fmcws/backend

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\Activate.ps1     # Windows PowerShell

# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
cp .env.example .env

# Запустить
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health

# Тестовое событие
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
```

**Ожидаемый ответ:**
```json
{
  "id": "event-uuid",
  "risk_score": 30.0,
  "risk_level": "medium",
  "triggered_rules": ["LOGIN_NEW_DEVICE"],
  "show_warning": true,
  "warning_message": "Обнаружена необычная активность. Если это не вы — заблокируйте карту."
}
```

---

## ⚙️ Конфигурация

Все параметры задаются в `backend/.env`:

```env
# Аутентификация
API_KEY=demo-fmcws-api-key-change-in-prod   # ← СМЕНИТЬ В PRODUCTION
SECRET_KEY=change-this-secret-key            # ← СМЕНИТЬ В PRODUCTION

# База данных
DATABASE_URL=sqlite+aiosqlite:///./fmcws.db
# Для production:
# DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/fmcws

# Webhook для уведомлений в банк
BANK_WEBHOOK_URL=https://your-bank.example.com/webhook/fraud

# Пороги риск-скора
WARN_THRESHOLD_MEDIUM=31    # medium:   31–60
WARN_THRESHOLD_HIGH=61      # high:     61–85
WARN_THRESHOLD_CRITICAL=86  # critical: 86–100
```

| Параметр | По умолчанию | Описание |
|---|---|---|
| `API_KEY` | demo-key | Ключ для заголовка `X-API-Key` |
| `SECRET_KEY` | (сменить) | Ключ подписи |
| `DATABASE_URL` | SQLite | URL базы данных |
| `BANK_WEBHOOK_URL` | `""` | Webhook при критическом риске |
| `WARN_THRESHOLD_MEDIUM` | `31` | Нижний порог medium |
| `WARN_THRESHOLD_HIGH` | `61` | Нижний порог high |
| `WARN_THRESHOLD_CRITICAL` | `86` | Нижний порог critical |

> ⚠️ Никогда не коммитьте `.env` с реальными ключами. Файл добавлен в `.gitignore`.

---

## 📡 API Reference

Все запросы требуют заголовка аутентификации:

```
X-API-Key: <ваш_ключ>
```

### Endpoints

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/health` | Проверка работоспособности |
| `GET` | `/v1/stats` | Статистика событий и алертов |
| `POST` | `/v1/events` | **Приём и скоринг события** |
| `GET` | `/v1/alerts` | Список алертов |
| `PATCH` | `/v1/alerts/{id}` | Обновление статуса алерта |
| `GET` | `/v1/cases` | Список кейсов |
| `POST` | `/v1/cases` | Создание кейса вручную |
| `PATCH` | `/v1/cases/{id}` | Обновление кейса |
| `GET` | `/v1/rules` | Список правил скоринга |
| `POST` | `/v1/rules` | Создание кастомного правила |
| `PATCH` | `/v1/rules/{id}` | Обновление правила |
| `DELETE` | `/v1/rules/{id}` | Удаление правила |

### POST /v1/events — схема запроса

```json
{
  "session_id":  "string (UUID сессии клиента)",
  "client_id":   "string (псевдонимизированный ID клиента)",
  "event_type":  "string (код события, см. таблицу правил)",
  "channel":     "web | mobile | atm | call_center",
  "ip_address":  "string (IPv4/IPv6)",
  "extra": {
    "is_new_device":  true,
    "amount":         5000.00,
    "recipient_id":   "string",
    "app_version":    "2.1.0"
  }
}
```

### Коды ответов

| HTTP | Описание |
|---|---|
| `200` | Событие обработано, возвращён скор и уровень риска |
| `401` | Неверный или отсутствующий `X-API-Key` |
| `422` | Ошибка валидации тела запроса |
| `500` | Внутренняя ошибка сервера |

### Примеры

**Критический сценарий — смена контактов + крупный перевод:**

```bash
# 1. Смена контактных данных
curl -X POST http://localhost:8000/v1/events \
  -H "X-API-Key: demo-fmcws-api-key-change-in-prod" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","client_id":"c1","event_type":"CONTACT_CHANGE","channel":"web","ip_address":"1.2.3.4","extra":{}}'

# 2. Перевод крупной суммы (скор → critical)
curl -X POST http://localhost:8000/v1/events \
  -H "X-API-Key: demo-fmcws-api-key-change-in-prod" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","client_id":"c1","event_type":"TRANSFER_CONFIRM","channel":"web","ip_address":"1.2.3.4","extra":{"amount":9000,"is_new_recipient":true}}'
```

**Список алертов с фильтрацией:**

```bash
curl "http://localhost:8000/v1/alerts?risk_level=critical&status=open" \
  -H "X-API-Key: demo-fmcws-api-key-change-in-prod"
```

**Статистика:**

```bash
curl http://localhost:8000/v1/stats \
  -H "X-API-Key: demo-fmcws-api-key-change-in-prod"
```

---

## 🛡 Встроенные правила скоринга

14 правил, покрывающих основные векторы социальной инженерии и компрометации аккаунта:

| # | Код правила | Триггер | +Score | Описание |
|---|---|---|:---:|---|
| 1 | `LOGIN_NEW_DEVICE` | `LOGIN_SUCCESS` | **+30** | Вход с нового/неизвестного устройства |
| 2 | `LOGIN_FAIL_MULTIPLE` | `LOGIN_FAIL` | **+25** | 3 и более неудачных попытки входа подряд |
| 3 | `NEW_RECIPIENT_TRANSFER` | `TRANSFER_CONFIRM` | **+40** | Перевод новому получателю |
| 4 | `CONTACT_CHANGE_BEFORE_TRANSFER` | `TRANSFER_CONFIRM` | **+35** | Смена контактов в той же сессии перед переводом |
| 5 | `ATYPICAL_TIME` | любое | **+20** | Активность в период 00:00–05:59 |
| 6 | `PARALLEL_SESSION` | `PARALLEL_SESSION_DETECTED` | **+30** | Обнаружены параллельные активные сессии |
| 7 | `IP_CHANGE_IN_SESSION` | `IP_CHANGE` | **+15** | Изменение IP-адреса в рамках сессии |
| 8 | `LIMIT_CHANGE` | `LIMIT_CHANGE` | **+25** | Изменение лимитов на операции |
| 9 | `CONTACT_CHANGE` | `CONTACT_CHANGE` | **+20** | Смена номера телефона или e-mail |
| 10 | `OTP_MULTIPLE_REQUESTS` | `OTP_REQUEST` | **+20** | 3+ запросов OTP за последние 5 минут |
| 11 | `NETWORK_CHANGE` | `NETWORK_CHANGE` | **+15** | Смена ASN / интернет-провайдера |
| 12 | `VIRTUAL_CARD_ISSUE` | `VIRTUAL_CARD_ISSUE` | **+15** | Выпуск виртуальной карты |
| 13 | `HIGH_AMOUNT_TRANSFER` | `TRANSFER_CREATE` | **+20** | Сумма перевода превышает 5 000 (`extra.amount`) |
| 14 | `APP_VERSION_CHANGE` | `APP_VERSION_CHANGE` | **+10** | Изменение версии мобильного приложения |

> Все правила расширяемы через `POST /v1/rules` без перезапуска сервиса.

---

## 🚦 Уровни риска

| Уровень | Score | Действие системы | Рекомендуемая реакция |
|---|:---:|---|---|
| 🟢 **Низкий** | 0 – 30 | `allow` — нет предупреждений | Стандартный поток |
| 🟡 **Средний** | 31 – 60 | `step_up` — предупреждение клиенту | Доп. подтверждение операции |
| 🟠 **Высокий** | 61 – 85 | `manual_review` — усиленное предупреждение | Звонок клиенту / блокировка |
| 🔴 **Критический** | 86 – 100 | `block` + webhook в банк | Блокировка сессии, инцидент |

Пороги настраиваются через переменные окружения без деплоя.

---

## 🌐 Web SDK

Подключение на любую HTML-страницу без зависимостей:

```html
<script src="fmcws-sdk.js"></script>
<script>
  var fmcws = new FMCWS({
    apiUrl:    'https://fmcws.bank.by',
    apiKey:    'YOUR_API_KEY',
    clientId:  'PSEUDONYMIZED_CLIENT_ID', // хэш ID, не реальный
    debug:     false,
    autoTrack: true,  // автоматический трекинг форм
  });
  fmcws.init();
</script>
```

**Ручной трекинг события:**

```javascript
fmcws.track('LOGIN_SUCCESS', {
  is_new_device: true
});
```

**Автотрекинг форм через data-атрибуты:**

```html
<form
  data-fmcws-event="TRANSFER_CONFIRM"
  data-fmcws-amount="1500"
>
  <!-- поля формы -->
  <button type="submit">Подтвердить перевод</button>
</form>
```

**Обработка предупреждений:**

```javascript
fmcws.onWarning(function(warning) {
  // warning.level: 'medium' | 'high' | 'critical'
  // warning.message: текст предупреждения
  showCustomAlert(warning.message, warning.level);
});
```

---

## 📱 Mobile SDK

### Android (Kotlin)

**Инициализация в `Application.onCreate()`:**

```kotlin
FmcwsSDK.init(
    context = this,
    config = FmcwsConfig(
        apiUrl  = "https://fmcws.bank.by",
        apiKey  = BuildConfig.FMCWS_API_KEY, // из BuildConfig, не хардкодить
        clientId = "anonymous"
    )
)
```

**Трекинг событий:**

```kotlin
// Простое событие
FmcwsSDK.track("LOGIN_SUCCESS")

// С дополнительными данными
FmcwsSDK.track("TRANSFER_CREATE", mapOf(
    "amount"       to 9500.0,
    "is_new_device" to true
))
```

**Обработка предупреждений:**

```kotlin
FmcwsSDK.setWarningListener(object : FmcwsWarningListener {
    override fun onWarning(warning: FmcwsWarning) {
        runOnUiThread {
            AlertDialog.Builder(context)
                .setTitle("Внимание")
                .setMessage(warning.message)
                .setPositiveButton("Понял") { _, _ -> }
                .show()
        }
    }
})
```

---

### iOS (Swift)

**Инициализация в `AppDelegate` или `@main`:**

```swift
FmcwsSDK.shared.initialize(config: FmcwsConfig(
    apiURL:   URL(string: "https://fmcws.bank.by")!,
    apiKey:   ProcessInfo.processInfo.environment["FMCWS_API_KEY"] ?? "",
    clientId: "anonymous"
))
```

**Трекинг событий:**

```swift
// Простое событие
FmcwsSDK.shared.track("LOGIN_SUCCESS")

// С параметрами
FmcwsSDK.shared.track("TRANSFER_CONFIRM", extra: [
    "amount":         9500.0,
    "is_new_device":  true,
    "recipient_id":   "rec-hash-001"
])
```

**Обработка предупреждений (делегат):**

```swift
class PaymentViewController: UIViewController, FmcwsWarningDelegate {

    override func viewDidLoad() {
        super.viewDidLoad()
        FmcwsSDK.shared.warningDelegate = self
    }

    func fmcws(didReceiveWarning warning: FmcwsWarning) {
        let alert = UIAlertController(
            title:   "Внимание",
            message: warning.message,
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "Понял", style: .default))
        present(alert, animated: true)
    }
}
```

---

## 🖥 Admin Console

Откройте `admin-console/index.html` в браузере:

1. В поле **URL** введите `http://localhost:8000`
2. В поле **API Key** введите `demo-fmcws-api-key-change-in-prod`
3. Нажмите **Подключиться**

**Разделы панели:**

| Раздел | Описание |
|---|---|
| Дашборд | Метрики: события за 24ч, алерты по уровням, тренды |
| Алерты | Список с фильтром по уровню и статусу, смена статуса |
| Кейсы | Кейс-менеджмент: создание, назначение, закрытие |
| События | Полный журнал событий с риск-скором |
| Правила | CRUD кастомных правил без перезапуска сервиса |

---

## 📁 Структура проекта

```
fmcws/
│
├── backend/                        # FastAPI backend (Python 3.12)
│   ├── app/
│   │   ├── main.py                 # Точка входа, lifespan, CORS
│   │   ├── config.py               # Настройки (pydantic-settings)
│   │   ├── database.py             # SQLAlchemy async engine + сессия
│   │   ├── models.py               # ORM: Event, Alert, Case, Rule, AuditLog
│   │   ├── schemas.py              # Pydantic схемы запросов и ответов
│   │   ├── auth.py                 # X-API-Key middleware
│   │   ├── scoring.py              # Скоринговый движок + 14 встроенных правил
│   │   └── routers/
│   │       ├── events.py           # POST /v1/events — приём и скоринг
│   │       ├── alerts.py           # GET/PATCH /v1/alerts
│   │       ├── cases.py            # GET/POST/PATCH /v1/cases
│   │       ├── rules.py            # CRUD /v1/rules
│   │       └── health.py           # GET /health, GET /v1/stats
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── web-sdk/
│   ├── fmcws-sdk.js                # Vanilla JS SDK (zero dependencies)
│   └── example.html                # Пример интеграции
│
├── admin-console/
│   └── index.html                  # React SPA (CDN, без сборки)
│
├── mobile-sdk/
│   ├── android/
│   │   ├── FmcwsSDK.kt             # Kotlin SDK (OkHttp + Coroutines)
│   │   └── ExampleIntegration.kt   # Пример интеграции
│   └── ios/
│       ├── FmcwsSDK.swift          # Swift SDK (URLSession + CryptoKit)
│       └── ExampleIntegration.swift
│
└── docker-compose.yml
```

---

## 🔧 Стек технологий

| Компонент | Технология |
|---|---|
| **Backend** | Python 3.12, FastAPI |
| **ORM** | SQLAlchemy (async) |
| **Валидация** | Pydantic v2 + pydantic-settings |
| **ASGI** | Uvicorn / Gunicorn |
| **База данных** | SQLite (dev) / PostgreSQL (prod) |
| **Auth** | X-API-Key middleware |
| **Admin UI** | React (CDN), без сборки |
| **Web SDK** | Vanilla JS, zero dependencies |
| **Android SDK** | Kotlin, OkHttp, Coroutines |
| **iOS SDK** | Swift, URLSession, CryptoKit |
| **Деплой** | Docker + docker-compose |

---

## ✅ Production checklist

```
Безопасность
  [ ] Сменить API_KEY в .env (убрать demo-key)
  [ ] Сменить SECRET_KEY на криптографически стойкий
  [ ] Ограничить CORS origins в main.py
  [ ] Настроить TLS/HTTPS (nginx reverse proxy)
  [ ] Убедиться что .env не попал в git

База данных
  [ ] Заменить SQLite на PostgreSQL
      DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/fmcws
  [ ] Настроить бэкапы БД
  [ ] Запустить миграции (Alembic)

Интеграции
  [ ] Установить BANK_WEBHOOK_URL для критических алертов
  [ ] Проверить доставку webhook (тест с curl)
  [ ] Настроить псевдонимизацию client_id

Инфраструктура
  [ ] Настроить ротацию логов
  [ ] Подключить мониторинг (Prometheus / Grafana)
  [ ] Настроить алерты на error rate и latency
  [ ] Провести нагрузочное тестирование
  [ ] Настроить автозапуск (systemd / k8s)

Комплаенс
  [ ] Проверить соответствие 152-ФЗ (псевдонимизация client_id)
  [ ] Задокументировать политику хранения логов
  [ ] Настроить ролевую модель доступа к Admin Console
```

---

## 📄 Лицензия

MIT License — свободное использование в коммерческих и некоммерческих проектах.

---

<div align="center">

**FMCWS** · FastAPI · SQLAlchemy · Kotlin · Swift · Docker

*Мониторинг мошенничества в реальном времени — для банков и финтех-компаний*

</div>
