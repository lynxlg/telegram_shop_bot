---
title: Engineering Documentation Index
doc_kind: engineering
doc_function: index
purpose: Навигация по engineering-level документации этого репозитория.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
---

# Engineering Documentation Index

Каталог `memory-bank/engineering/` фиксирует инженерные правила этого репозитория: как здесь тестируют код, какие локальные соглашения по Python/Aiogram/SQLAlchemy считаются canonical и где агенту нужно останавливаться на контрольной точке.

- Рабочий язык project-specific документации и агентского взаимодействия по этому репозиторию — русский, если пользователь явно не просит иное.

- [Testing Policy](testing-policy.md) — как в проекте разделяются `unit` и `integration`, какие локальные команды считаются обязательными и какие Telegram/live-infra сценарии пока допустимы только вручную.
- [Autonomy Boundaries](autonomy-boundaries.md) — что агент может менять сам в коде и документации, а какие действия по БД, конфигу и внешним интеграциям нужно показывать на контрольной точке.
- [Coding Style](coding-style.md) — project-specific соглашения по Python, Aiogram handlers, SQLAlchemy models/services, Alembic и локальной сложности.
- [Git Workflow](git-workflow.md) — правила для `main`, формата commit message, требований к PR и когда worktree в этом репозитории оправдан.
- [ADR](../adr/README.md) — instantiated Architecture Decision Records проекта.
