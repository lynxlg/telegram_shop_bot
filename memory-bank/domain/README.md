---
title: Domain Documentation Index
doc_kind: domain
doc_function: index
purpose: Навигация по domain-level документации Telegram Shop Bot. Читать для фиксации бизнес-контекста, архитектурных границ и правил Telegram UI.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
---

# Domain Documentation Index

- [Project Problem Statement](problem.md) — общий продуктовый контекст Telegram-бота интернет-магазина: для кого он нужен, какие пользовательские потоки уже считаются базовыми и какие ограничения платформы влияют на все downstream-фичи.
- [Architecture Patterns](architecture.md) — реальные границы слоёв `handlers/services/models/keyboards`, правила доступа к PostgreSQL, lifecycle aiogram-приложения и ownership конфигурации.
- [Frontend](frontend.md) — правила для единственной UI-поверхности проекта: Telegram chat UI с reply/inline-клавиатурами и текстовыми сообщениями без отдельного web frontend.
