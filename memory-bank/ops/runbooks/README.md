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

В этом каталоге должны жить runbooks для повторяемых operational задач и инцидентов этого проекта.

Сейчас каталог не содержит project-specific runbooks. Это означает:

- повторяемые локальные действия пока документируются в [../development.md](../development.md);
- non-local operational процедуры ещё не оформлены и не должны подразумеваться по умолчанию;
- при появлении первой повторяемой операции или инцидентного сценария нужно завести отдельный runbook и добавить ссылку сюда.

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

## First Candidates

Когда в проекте появится необходимость, логично завести runbooks для:

- локального поднятия PostgreSQL и восстановления тестового контура;
- ручного seed каталога через `scripts/seed_catalog.sql`;
- диагностики падения бота при старте из-за `BOT_TOKEN` или `DATABASE_URL`;
- будущего non-local deploy / rollback, если такой процесс будет оформлен.
