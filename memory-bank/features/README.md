---
title: Feature Packages Index
doc_kind: feature
doc_function: index
purpose: Навигация по instantiated feature packages. Читать, чтобы найти существующую delivery-единицу или понять, где создавать новую.
derived_from:
  - ../dna/governance.md
  - ../flows/feature-flow.md
status: active
audience: humans_and_agents
---

# Feature Packages Index

Каталог `memory-bank/features/` хранит instantiated feature packages вида `FT-XXX/`.

## Rules

- Каждый package создается по правилам из [`../flows/feature-flow.md`](../flows/feature-flow.md).
- Для bootstrap используй шаблоны из [`../flows/templates/feature/`](../flows/templates/feature/).
- Если feature реализует или существенно меняет устойчивый сценарий проекта, она должна ссылаться на соответствующий `UC-*` из [`../use-cases/README.md`](../use-cases/README.md).
- Legacy feature-материалы, созданные до текущего flow, не считаются canonical package и должны жить только в archival subtree `legacy/`.

## Naming

- Базовый формат: `FT-XXX/`
- Вместо `XXX` используй идентификатор, принятый в проекте: issue id, ticket id или другой стабильный ключ
- Один package = одна delivery-единица

## Current State

- [`FT-ORD-001/`](FT-ORD-001/) — checkout из корзины: сбор контактов, подтверждение и создание заказа в PostgreSQL.
- [`FT-TRK-001/`](FT-TRK-001/) — пользовательский просмотр статуса активных заказов из главного меню.
- [`FT-NTF-001/`](FT-NTF-001/) — автоматические уведомления покупателю после смены статуса заказа оператором или администратором.
- [`FT-OPS-001/`](FT-OPS-001/) — операторский workflow просмотра активных заказов и смены их статусов в Telegram.
- [`FT-ADM-001/`](FT-ADM-001/) — административное управление категориями и товарами каталога внутри Telegram.
- Исторические материалы ранних задач вынесены в [`legacy/README.md`](legacy/README.md) и не участвуют в authoritative feature governance.
- Их устойчивые продуктовые контракты уже мигрированы в `domain/*` и `use-cases/*`; `legacy/` сохраняет только архивный след происхождения.
