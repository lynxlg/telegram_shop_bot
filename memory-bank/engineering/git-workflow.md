---
title: Git Workflow
doc_kind: engineering
doc_function: convention
purpose: Project-specific git workflow репозитория: default branch, commit conventions, PR expectations и правила использования worktree.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
---

# Git Workflow

## Default Branch

- Основная ветка репозитория — `main`.

## Commits

- Текущая история использует короткие commit messages с auto-close semantics: `Closes #1`, `Closes #2`, `Closes #3`. Для задач, привязанных к issue, это и есть локальный canonical pattern.
- Если изменение не связано с issue, commit message всё равно должен быть коротким и предметным, без шумовых префиксов.
- Не смешивай в одном commit независимые изменения кода, документации и bootstrap-инфраструктуры, если их можно отделить без потери связности.

## Pull Requests

- Перед PR должны быть зелёными canonical local checks для затронутого слоя: минимум relevant `pytest`, а для shell/bootstrap-изменений также совместимость с CI smoke.
- PR title должен быть коротким и предметным; если PR закрывает issue, body должен явно ссылаться на него, даже если auto-close уже есть в commit.
- В body PR зафиксируй три вещи: что изменено, чем это проверено локально, какие manual-only gaps или риски остаются.
- Если PR меняет schema, callback contract или внешний UX flow бота, в body нужно отдельно указать миграцию/rollback и затронутые пользовательские сценарии.

## Worktrees

- Worktree допустим как вспомогательный инструмент для параллельных задач, но репозиторий не требует его по умолчанию.
- После `git worktree add` дополнительный bootstrap нужен только если в новом дереве отсутствуют `.venv`, `.env` или локальный PostgreSQL-контекст для integration tests.
- Не используй worktree как предлог держать незавершённые несвязанные изменения месяцами; короткоживущие изолированные ветки предпочтительнее.
