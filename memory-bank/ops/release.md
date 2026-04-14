---
title: Release And Deployment
doc_kind: ops
doc_function: canonical
purpose: Фиксирует текущее состояние релизного процесса Telegram Shop Bot и явно отделяет известные факты от ещё не описанного deployment workflow.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
---

# Release And Deployment

## Release Flow

Подтверждённого end-to-end deployment workflow в репозитории пока нет. На сегодня известны только следующие факты:

1. CI запускается через [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml) на `push` в `main`, `pull_request` и `workflow_dispatch`.
2. CI сейчас проверяет shell/markdown/bootstrap smoke, но не описывает production deployment бота.
3. Команды для сборки контейнера, выкладки в hosting или создания GitHub release в репозитории не зафиксированы.

Поэтому canonical безопасное правило сейчас такое: релизный процесс считается manual и требует явного human-owned решения на каждом шаге вне локального окружения.

## Release Commands

Подтверждённые команды только для локальной pre-release проверки:

```bash
.venv/bin/pytest tests/ -v -m unit
.venv/bin/pytest tests/ -v --run-integration
./scripts/run-tests.sh
docker compose up -d postgres
```

Safety rules:

- Любой deploy вне localhost требует отдельного подтверждения человека.
- Изменения конфигурации runtime, секретов, webhook/polling режима, схемы БД и инфраструктуры не считаются безопасными автоматическими release steps.
- Пока не задокументирован canonical deployment target, агент не должен выдумывать `make deploy`, `docker push`, `kubectl apply` или аналогичные команды.

## Release Test Plan

Если начинается реальный release process, перед первой выкладкой стоит завести отдельный release test plan. До появления production-like окружения minimum viable pre-release check для этого проекта:

- зелёный unit-прогон;
- зелёный integration-прогон с PostgreSQL;
- ручная проверка базового сценария бота в Telegram:
  - `/start`
  - навигация по каталогу
  - открытие карточки товара
  - добавление товара в корзину
  - изменение количества в корзине

Отдельный release test plan файл ещё не является established process и должен появиться вместе с формализацией релизов.

## Rollback

- Rollback unit для non-local deployment не задокументирован.
- Без отдельного deployment workflow нельзя утверждать ни rollback-команду, ни обратимость миграций/данных.
- До появления production process safest fallback — остановиться на локальной верификации и эскалировать владельцу окружения.
