---
title: Stages And Non-Local Environments
doc_kind: ops
doc_function: canonical
purpose: Фиксирует текущее состояние non-local окружений Telegram Shop Bot и ограничения на работу вне localhost.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
---

# Stages And Non-Local Environments

На момент адаптации `memory-bank` в репозитории не задокументированы развернутые `staging`, `sandbox` или `production` окружения для этого бота. Поэтому этот документ фиксирует именно отсутствие подтверждённых operational entrypoints.

## Environment Inventory

| Environment | Purpose | Access path | Notes |
| --- | --- | --- | --- |
| `local` | Разработка и тесты | `.venv/bin/python -m app.main`, `pytest`, `docker compose up -d postgres` | Единственное подтверждённое окружение |
| `production` | Unknown | Not documented | Любые действия требуют явного подтверждения человека |
| `staging` | Unknown | Not documented | Нельзя предполагать наличие URL, namespace или доступа |

## Common Operations

Реально подтверждены только локальные операции:

```bash
.venv/bin/python -m app.main
.venv/bin/pytest tests/ -v -m unit
.venv/bin/pytest tests/ -v --run-integration
docker compose up -d postgres
```

Для non-local операций текущее правило такое:

- read-only доступ к логам, health checks, БД, контейнерам и secret stores не задокументирован;
- mutating actions вне localhost не разрешены по умолчанию;
- если появится реальный runtime entrypoint, его нужно добавить сюда до того, как он будет считаться canonical.

## Credentials And Access

- Процедура выдачи доступов к non-local окружениям в репозитории не описана.
- Реальные credentials, jump-hosts, namespaces, dashboard URLs и secret stores отсутствуют в authoritative docs этого проекта.
- Любая попытка восстановить их по косвенным признакам должна считаться недопустимым обходом процесса.

## Version And Health Checks

- Для локального окружения health-проверка сводится к успешному старту `.venv/bin/python -m app.main` и прохождению тестов.
- HTTP health endpoint в проекте не задокументирован.
- Способ проверки deployed version для non-local окружений не определён.

## Logs And Observability

- Локальные логи пишутся стандартным Python logging в stdout/stderr при запуске [app/main.py](../../app/main.py).
- Metrics, traces, error tracker и dashboards для non-local runtime в проектной документации не зафиксированы.

## Test Data And Smoke Targets

- Для локальной БД можно использовать [scripts/seed_catalog.sql](../../scripts/seed_catalog.sql).
- Demo accounts, staging tenants и production-safe smoke users не задокументированы.

## Update Rule

Если появятся реальные `staging` или `production` entrypoints, документ должен быть обновлён раньше downstream-инструкций и runbooks, которые на них ссылаются.
