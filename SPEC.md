# Техническое задание: Webhook Relay Service

## 1. Стек и ограничения
- **Python 3.12+**, **FastAPI**, **Pydantic v2**
- **SQLAlchemy 2.0** (асинхронный драйвер `asyncpg` для FastAPI, синхронный `psycopg` или `asyncio.run` для воркеров Celery) + **Alembic** для миграций.
- **Celery 5+** с брокером и бэкендом результатов на **Redis**.
- **HTTPX** для отправки исходящих вебхуков.
- **Docker & Docker Compose** для локального запуска и тестов.
- **Pytest** + `pytest-asyncio` + `httpx` (AsyncClient) для тестирования.
- **Ruff** - линтёр
- **ci** - запуск тестов, запуск линтёров

## 2. Структура проекта
```text
├── app/
│   ├── api/            # Роутеры FastAPI (v1)
│   ├── core/           # Конфиг (pydantic-settings), безопасность, логирование
│   ├── db/             # Сессии БД, базовые модели SQLAlchemy
│   ├── models/         # Таблицы: Endpoint, Event, DeliveryAttempt
│   ├── schemas/        # Pydantic-схемы запросов и ответов
│   ├── services/       # Бизнес-логика (генерация HMAC-SHA256 подписи)
│   └── worker/         # Конфиг Celery и задачи отправки вебхуков
├── migrations/         # Миграции Alembic
├── tests/              # Unit и интеграционные тесты
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── pyproject.toml
```

## 3. Схема базы данных (SQLAlchemy)
1. **endpoints**: `id` (UUID), `url` (String), `secret` (String), `is_active` (Boolean), `created_at` (DateTime).
2. **events**: `id` (UUID), `endpoint_id` (FK), `event_type` (String), `payload` (JSONB), `status` (Enum: `pending`, `delivered`, `failed`), `created_at` (DateTime).
3. **delivery_attempts**: `id` (UUID), `event_id` (FK), `attempt_number` (Int), `status_code` (Int, nullable), `response_body` (Text, nullable), `error_message` (Text, nullable), `created_at` (DateTime).

## 4. API Эндпоинты
- `POST /api/v1/endpoints` — регистрация URL-получателя (генерирует `secret` автоматически).
- `GET /api/v1/endpoints/{id}` — получение информации о подписке.
- `POST /api/v1/events` — прием события (`endpoint_id`, `event_type`, `payload`). Сохраняет в БД со статусом `pending` и ставит задачу в Celery. Возвращает `202 Accepted` с `event_id`.
- `GET /api/v1/events/{id}` — статус события и список всех `delivery_attempts`.
- `GET /health` — проверка доступности PostgreSQL и Redis.

## 5. Логика работы Celery Worker
- Задача `deliver_webhook(event_id: str)`:
  - Формирует заголовок `X-Webhook-Signature` (HMAC-SHA256 от тела запроса с использованием `endpoint.secret`).
  - Отправляет `POST` запрос на `endpoint.url` с таймаутом 5 секунд.
  - Записывает результат в таблицу `delivery_attempts`.
  - Если ответ `2xx`: обновляет `event.status = 'delivered'`.
  - Если ответ `5xx`, `429` или сетевой таймаут: делает retry задачи (максимум 3 попытки с задержкой 2s, 4s, 8s). Если попытки исчерпаны — ставит `event.status = 'failed'`.
  - Если ответ `4xx` (кроме 429): не ретраит, сразу ставит `event.status = 'failed'`.

## 6. Критерии приемки и самопроверки
Агент обязан запускать тесты и линтер после каждого завершенного модуля. Задача считается выполненной только если:
1. `docker compose up -d --build` поднимает все сервисы без ошибок, миграции Alembic применяются автоматически.
2. Команда `pytest` проходит на 100% без падений и ворнингов.
3. Тестами покрыты:
   - Успешная доставка вебхука и проверка валидности заголовка `X-Webhook-Signature`.
   - Сценарий с возвратом `500 Internal Server Error` от получателя и проверка того, что создалось 3 записи в `delivery_attempts`, а финальный статус стал `failed`.
   - Сценарий с `400 Bad Request` (проверка отсутствия лишних ретраев).
