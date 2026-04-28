---
title: Configuration Guide
doc_kind: ops
doc_function: canonical
purpose: Описывает фактическую модель конфигурации Telegram Shop Bot: schema-owner, env-файлы и ключевые runtime contracts.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
---

# Configuration Guide

## Configuration Architecture

- Canonical schema-owner конфигурации: [app/config.py](../../app/config.py), класс `Settings`.
- Конфигурация typed и строится через `pydantic-settings`.
- Defaults объявлены прямо в `Settings`.
- Runtime values приходят из process environment и `.env`.
- Неизвестные поля игнорируются за счёт `extra="ignore"`.

### File Layout

```text
app/config.py        # typed schema и defaults
.env                 # локальные runtime overrides, читается приложением
.env.local           # локальные overrides через .envrc для shell-команд
tests/.env.test      # test-only конфигурация для pytest fixtures
.envrc               # экспорт .env/.env.local и вспомогательного PORT
```

### Ownership Rules

1. `app/config.py` владеет формой и default-значениями runtime config.
2. `.env` и process env переопределяют defaults для локального запуска.
3. `tests/.env.test` владеет test-specific подключением к БД и test token для pytest.
4. `.envrc` не владеет runtime schema приложения; он только экспортирует локальные env vars в shell и подставляет `PORT` для tooling.

Использование в коде:

```python
from app.config import get_settings

settings = get_settings()
settings.bot_token
settings.database_url
```

## Naming Convention For Env Vars

- Проект не использует отдельный префикс для env vars.
- Имена env vars следуют именам полей `Settings` в верхнем регистре с подчёркиваниями:
  - `bot_token` -> `BOT_TOKEN`
  - `database_url` -> `DATABASE_URL`
  - `yookassa_shop_id` -> `YOOKASSA_SHOP_ID`
  - `yookassa_secret_key` -> `YOOKASSA_SECRET_KEY`
  - `yookassa_return_url` -> `YOOKASSA_RETURN_URL`
  - `yookassa_webhook_host` -> `YOOKASSA_WEBHOOK_HOST`
  - `yookassa_webhook_port` -> `YOOKASSA_WEBHOOK_PORT`
  - `yookassa_webhook_path` -> `YOOKASSA_WEBHOOK_PATH`
- Вложенной структуры и специального separator для env vars сейчас нет.
- `PORT` существует только в shell context через `.envrc` и не читается `Settings`.

## Documenting Important Variables

| Variable | Description | Default | Owner |
| --- | --- | --- | --- |
| `BOT_TOKEN` | Telegram bot token для runtime | `TEST_BOT_TOKEN` | app/runtime |
| `DATABASE_URL` | Async SQLAlchemy DSN | `postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_shop_bot` | app/runtime |
| `YOOKASSA_SHOP_ID` | Shop ID YooKassa API | `None` | payment runtime |
| `YOOKASSA_SECRET_KEY` | Secret key YooKassa API | `None` | payment runtime |
| `YOOKASSA_RETURN_URL` | URL возврата redirect-платежа | `https://example.com/yookassa/return` | payment runtime |
| `YOOKASSA_WEBHOOK_HOST` | Host встроенного webhook listener | `0.0.0.0` | payment runtime |
| `YOOKASSA_WEBHOOK_PORT` | Port встроенного webhook listener | `8080` | payment runtime |
| `YOOKASSA_WEBHOOK_PATH` | Path встроенного webhook listener | `/webhooks/yookassa` | payment runtime |
| `PORT` | Вспомогательная переменная shell/bootstrap tooling | задаётся `.envrc` через `port-selector`, если не указана | bootstrap tooling |

## Secrets

- Секреты в репозиторий не коммитятся; локально они должны приходить через `.env` или внешние env vars.
- Минимальный секрет для runtime: `BOT_TOKEN`.
- Для online payment секретами также считаются `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY`.
- `DATABASE_URL` может содержать пароль, поэтому его также считать секретом.
- На текущий момент в проектной документации не зафиксирован внешний secret manager для non-local окружений; до появления такого источника нельзя придумывать процедуру выдачи секретов.

## Test Configuration

- `tests/.env.test` используется только тестами и не должен применяться для runtime бота.
- Integration tests ожидают DSN на локальный PostgreSQL `localhost:55432` и отдельную БД `shop_bot_test`.
