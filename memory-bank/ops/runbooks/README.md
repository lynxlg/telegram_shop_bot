---
title: Runbooks Index
doc_kind: ops
doc_function: index
purpose: Точка входа в operational runbooks Telegram Shop Bot.
derived_from:
  - ../../dna/governance.md
status: active
audience: humans_and_agents
---

# Runbooks Index

В этом каталоге живут runbooks для повторяемых operational задач и инцидентов этого проекта.

## Current Runbooks

- [PostgreSQL Integration Tests Via Docker](postgres-integration-tests.md) — как прогонять `pytest --run-integration` через Docker PostgreSQL, что делать при sandbox/socket проблемах и почему evidence-команды нужно запускать последовательно.

Каждый runbook должен отвечать на вопросы:

- что является триггером;
- что проверить сначала;
- какие команды выполнять;
- какой результат ожидать;
- как безопасно откатиться;
- кому и когда эскалировать проблему.

## Suggested Structure

1. Summary
2. Trigger / symptoms
3. Safety notes
4. Diagnosis
5. Resolution
6. Rollback
7. Escalation

## Next Candidates

Когда в проекте появится необходимость, логично завести runbooks для:

- ручного seed каталога через `scripts/seed_catalog.sql`;
- диагностики падения бота при старте из-за `BOT_TOKEN` или `DATABASE_URL`;
- будущего non-local deploy / rollback, если такой процесс будет оформлен.
