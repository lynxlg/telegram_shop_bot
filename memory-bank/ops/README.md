---
title: Operations Index
doc_kind: ops
doc_function: index
purpose: Навигация по операционной документации проекта. Читать при локальной разработке, работе с конфигурацией, описании релиза и заведении runbooks.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
---

# Operations Index

Секция `ops/` фиксирует только operational-факты этого репозитория. Общий bootstrap учебного шаблона остаётся в корневых [SETUP.md](../../SETUP.md) и [AI-SETUP-README.md](../../AI-SETUP-README.md) и не заменяет project-specific runtime docs.

- [Development Environment](development.md) — как подготовить локальное окружение, поднять PostgreSQL, запустить бота и выполнить test-команды; отсюда же есть маршрут к runbook по integration tests через Docker.
- [Configuration](config.md) — где живёт schema конфигурации, какие env vars проект читает и как обращаться с секретами.
- [Stages And Non-Local Environments](stages.md) — текущее состояние non-local окружений и ограничения на работу вне localhost.
- [Release And Deployment](release.md) — что известно о релизном процессе сейчас и какие шаги должны быть подтверждены отдельно.
- [Runbooks](runbooks/README.md) — индекс operational runbooks, включая runbook по integration tests через Docker PostgreSQL и sandbox-boundary.
