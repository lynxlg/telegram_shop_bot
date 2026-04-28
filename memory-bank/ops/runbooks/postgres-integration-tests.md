---
title: PostgreSQL Integration Tests Via Docker
doc_kind: ops
doc_function: canonical
purpose: "Runbook для прогонов integration tests против Docker PostgreSQL и диагностики типовых проблем с подключением, sandbox и teardown."
derived_from:
  - ../development.md
  - ../../engineering/testing-policy.md
status: active
audience: humans_and_agents
---

# PostgreSQL Integration Tests Via Docker

## Summary

Этот runbook описывает, как надёжно прогонять `pytest --run-integration` в репозитории `telegram_shop_bot`, когда source of truth для тестов — Docker-контейнер `telegram_shop_bot_postgres`.

Ключевой факт: canonical Docker PostgreSQL в проекте опубликован на `localhost:55432`, а `tests/.env.test` по умолчанию смотрит на `localhost:5432`. Поэтому перед прогоном через Docker нужно либо временно направить test DSN на `55432`, либо подготовить эквивалентный локальный forward. После прогона test DSN нужно вернуть в исходное состояние.

## Trigger / Symptoms

- Нужен честный integration verify по `pytest --run-integration`.
- Тесты skip-аются с сообщением про невозможность создать test DB.
- `asyncpg` не подключается к локальной Docker PostgreSQL.
- Evidence-прогоны падают на teardown с `deadlock detected`, `UndefinedTableError` или `connection was closed in the middle of operation`.

## Safety Notes

- Не меняй проектный `docker-compose.yml` только ради разового verify.
- Не оставляй `tests/.env.test` переписанным на `55432` после прогона.
- Не запускай несколько integration pytest-команд параллельно против одной и той же test DB `shop_bot_test`.
- Если sandbox блокирует локальные сокеты `asyncpg`, integration tests нужно запускать вне sandbox с явной эскалацией.

## Diagnosis

1. Проверить контейнер PostgreSQL:

```bash
sudo docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
```

Ожидаемый контейнер: `telegram_shop_bot_postgres`, порт `0.0.0.0:55432->5432/tcp`.

2. Проверить, какой DSN зашит в `tests/.env.test`:

```bash
sed -n '1p' tests/.env.test
```

3. Если integration tests skip-аются только внутри агентской среды, а контейнер живой, считать основной причиной sandbox/socket restriction, а не падение PostgreSQL.

4. Если failures появляются только при записи evidence, проверить, не были ли integration команды запущены параллельно. Для этого достаточно посмотреть последние логи на предмет:

- `deadlock detected`
- `UndefinedTableError`
- `connection was closed in the middle of operation`

Такие ошибки в этом проекте обычно означают гонку teardown fixture, а не product bug.

## Resolution

### 1. Поднять Docker PostgreSQL

```bash
sudo docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'
docker compose up -d postgres
```

Если контейнер уже `Up (...) healthy`, повторный `up -d` не обязателен.

### 2. Временно направить integration tests на Docker порт `55432`

В `tests/.env.test` временно заменить первую строку:

```text
DATABASE_URL=postgresql+asyncpg://lynx:password@localhost:55432/shop_bot_test?connect_timeout=3
```

После verify обязательно вернуть обратно canonical значение на `5432`.

### 3. Если integration path выполняется из агентской среды, запускать pytest вне sandbox

Canonical pattern:

```bash
.venv/bin/pytest tests/... -v --run-integration
```

Если внутри sandbox `asyncpg` падает на `PermissionError`/socket open, тот же pytest нужно перезапустить с эскалацией.

### 4. Гонять integration evidence только последовательно

Правильно:

```bash
.venv/bin/pytest tests/handlers/test_start.py tests/handlers/test_order_status.py -v --run-integration
.venv/bin/pytest tests/test_order_service.py -v --run-integration
```

Неправильно:

- несколько `pytest --run-integration` процессов одновременно;
- параллельная запись нескольких `CHK-*` evidence в фоне.

### 5. После verify вернуть `tests/.env.test`

Восстановить canonical строку:

```text
DATABASE_URL=postgresql+asyncpg://lynx:password@localhost:5432/shop_bot_test?connect_timeout=3
```

## Known Working Sequence

Ниже — последовательность, которая уже сработала в этом репозитории:

1. `sudo docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'`
2. Подтвердить, что `telegram_shop_bot_postgres` жив и слушает `55432`
3. Временно поменять `tests/.env.test` на `localhost:55432`
4. Запустить integration pytest вне sandbox
5. Если падают только отдельные product tests — чинить код
6. Если падают teardown/DDL ошибки — перезапустить evidence-команды последовательно
7. После успешных логов вернуть `tests/.env.test` на `5432`

## Expected Result

- `pytest --run-integration` реально подключается к Docker PostgreSQL, а не skip-ается
- test DB `shop_bot_test` создаётся и удаляется автоматически
- evidence-логи содержат `... passed ...`, без teardown deadlock/DDL race
- `tests/.env.test` после завершения снова указывает на `localhost:5432`

## Rollback

Если runbook использовался только для verify:

1. Вернуть `tests/.env.test` на `localhost:5432`
2. Остановить Docker PostgreSQL только если он был поднят специально:

```bash
docker compose stop postgres
```

Если контейнер использовался и для других локальных задач, не останавливать его автоматически.

## Escalation

- Если `sudo docker ps` не показывает `telegram_shop_bot_postgres`, а `docker compose up -d postgres` не поднимает контейнер — эскалировать как Docker/runtime issue.
- Если even outside sandbox `asyncpg` не подключается к `localhost:55432` — эскалировать как network/runtime issue, а не как bug в feature code.
- Если integration tests стабильно падают на product logic после корректного подключения — эскалировать уже в feature/code path.
