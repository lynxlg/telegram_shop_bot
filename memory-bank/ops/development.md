---
title: Development Environment
doc_kind: ops
doc_function: canonical
purpose: Локальная разработка Telegram Shop Bot: bootstrap, запуск бота, тесты и работа с локальной PostgreSQL.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
---

# Development Environment

## Scope

Этот документ покрывает только локальную разработку в репозитории `telegram_shop_bot`.
Bootstrap агентских CLI и shell tooling описан в [SETUP.md](../../SETUP.md); здесь фиксируются только команды и зависимости, нужные для самого бота.

## Setup

Минимальный рабочий путь:

```bash
make
direnv allow
.venv/bin/pip install -r requirements.txt -r requirements-test.txt
docker compose up -d postgres
```

Примечания:

- `make` и `direnv allow` относятся к bootstrap-окружению из [SETUP.md](../../SETUP.md).
- Проект ожидает локальный `.venv`; команды в `README.md` и скриптах используют `.venv/bin/...`.
- Если в локальной среде не хватает Python-зависимостей для приложения или тестов, устанавливай их в эту же `.venv`, а не в system Python.
- `.envrc` подхватывает `.env` и `.env.local`, а при отсутствии `PORT` пытается выставить его через `port-selector`.
- Для запуска бота нужен валидный `BOT_TOKEN`.
- Для работы с PostgreSQL нужен `DATABASE_URL`; если он не задан, приложение возьмёт default из [app/config.py](../../app/config.py), но этот default не совпадает с тестовым `docker-compose.yml`, поэтому для локальной работы лучше задавать явное значение в `.env`.

## Daily Commands

Canonical команды проекта:

```bash
.venv/bin/python -m app.main
.venv/bin/pytest tests/ -v -m unit
.venv/bin/pytest tests/ -v --run-integration
./scripts/run-tests.sh
docker compose up -d postgres
```

Что делает каждая команда:

- `.venv/bin/python -m app.main` — запускает polling-бота и перед стартом вызывает `init_db()`.
- `.venv/bin/pytest tests/ -v -m unit` — быстрый unit-прогон без PostgreSQL.
- `.venv/bin/pytest tests/ -v --run-integration` — включает integration tests, которые требуют доступный PostgreSQL.
- `./scripts/run-tests.sh` — полный pytest-прогон с coverage по `app/`.
- `docker compose up -d postgres` — поднимает единственный локальный сервис из `docker-compose.yml`.

## Application Runtime

- Entry point: [app/main.py](../../app/main.py)
- Bot factory: [app/bot.py](../../app/bot.py)
- Database bootstrap: [app/models/database.py](../../app/models/database.py)

При запуске приложение создаёт `Bot` и `Dispatcher`, подключает middleware и routers, вызывает `init_db()`, запускает polling, а при завершении закрывает bot session и SQLAlchemy engine.

## Browser Testing

У проекта нет web UI и локального HTTP-сервера.

- `PORT`, который выставляет `.envrc`, относится к bootstrap-среде и shell tooling, а не к runtime самого бота.
- Browser verification не является canonical способом проверки этого репозитория.
- Для пользовательских сценариев использовать automated tests и ручную проверку через Telegram-клиент только как manual-only дополнение.

## Database And Services

- Обязательный внешний сервис для integration tests: PostgreSQL 16 в Docker на `localhost:55432`.
- `docker-compose.yml` поднимает контейнер `telegram_shop_bot_postgres` с user `lynx`, password `password`, admin DB `postgres`.
- Integration tests используют [tests/.env.test](../../tests/.env.test) и отдельную БД `shop_bot_test`.
- Фикстуры в [tests/conftest.py](../../tests/conftest.py) автоматически создают тестовую БД, создают schema, а после тестов удаляют её.
- Приложение инициализирует schema через SQLAlchemy `Base.metadata.create_all`; alembic-конфигурация присутствует в репозитории, но текущий локальный workflow не задокументирован как canonical migration path.
- Для демонстрационных данных есть [scripts/seed_catalog.sql](../../scripts/seed_catalog.sql), который заполняет категории, товары и атрибуты.

## Known Pitfalls

- Default `DATABASE_URL` в [app/config.py](../../app/config.py) указывает на `postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_shop_bot`; контейнер из `docker-compose.yml` публикуется на `localhost:55432` и использует credentials `lynx/password`. Для локального запуска это нужно синхронизировать через `.env`.
- Integration tests пропускаются, если PostgreSQL недоступен или тестовую БД нельзя создать.
- Репозиторий содержит bootstrap-скрипты (`Makefile`, `scripts/test-setup.sh`, `scripts/test-ci.sh`) из учебного шаблона. Они полезны для окружения разработчика, но не заменяют команды запуска самого бота.
