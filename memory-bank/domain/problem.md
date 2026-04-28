---
title: Project Problem Statement
doc_kind: domain
doc_function: canonical
purpose: Каноничное описание продукта, проблемного пространства и целевых outcomes. Читать перед feature-спеками, чтобы не повторять общий контекст в каждой delivery-единице.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
canonical_for:
  - project_problem_statement
  - product_context
  - top_level_outcomes
---

# Project Problem Statement

Этот документ фиксирует общий продуктовый контекст `telegram_shop_bot`. Feature-документы должны ссылаться на него, а не переписывать базовый фон про Telegram-бот магазина в каждой delivery-единице.

## Boundary With PRD

- `domain/problem.md` — общий для всего проекта контекст: продукт, ключевые workflows, top-level outcomes и устойчивые ограничения.
- `prd/PRD-XXX-short-name.md` — инициативный слой: какая именно продуктовая проблема берется в работу сейчас, для каких пользователей и с каким scope.
- Если новый документ просто повторяет общий фон проекта и не вводит initiative-specific scope, PRD создавать не нужно.

## Product Context

Проект развивает Telegram-бота интернет-магазина на `Aiogram` и `PostgreSQL`. Основной пользователь — покупатель, который хочет пройти путь выбора товара прямо внутри Telegram без перехода на отдельный сайт и без обращения к менеджеру на каждом шаге.

Текущий реализованный scope покрывает вход через `/start`, просмотр иерархического каталога, открытие карточки товара с изображением по `image_url`, работу с корзиной и role-gated operational/admin сценарии, зафиксированные в канонических `UC-*` и feature packages. Эти сценарии уже считаются подтвержденной ценностью и не должны ломаться при развитии следующих фич.

Более широкое продуктовое направление из `PROJECT.md` по-прежнему включает оплату, расширенные админские операции и CRM-интеграции. Однако считать сценарий текущим фактом поведения можно только после его реализации в коде и фиксации в governed-слое `use-cases/*` и `features/*`; roadmap сам по себе не является источником истины.

## Core Workflows

- `WF-01` Регистрация и возврат в бот: пользователь отправляет `/start`, бот сохраняет или обновляет запись пользователя в таблице `users` и показывает role-aware главное меню.
- `WF-02` Навигация по каталогу: см. [`../use-cases/UC-001-browse-catalog-and-open-product.md`](../use-cases/UC-001-browse-catalog-and-open-product.md).
- `WF-03` Работа с корзиной: см. [`../use-cases/UC-002-manage-cart.md`](../use-cases/UC-002-manage-cart.md).
- `WF-04` Checkout и создание заказа: см. [`../use-cases/UC-003-checkout-and-create-order.md`](../use-cases/UC-003-checkout-and-create-order.md).
- `WF-05` Покупатель проверяет активные заказы: см. [`../use-cases/UC-004-check-active-order-status.md`](../use-cases/UC-004-check-active-order-status.md).
- `WF-06` Оператор или администратор меняет статус заказа: см. [`../use-cases/UC-005-manage-order-status.md`](../use-cases/UC-005-manage-order-status.md).
- `WF-07` Администратор управляет каталогом: см. [`../use-cases/UC-006-manage-catalog.md`](../use-cases/UC-006-manage-catalog.md).

## Outcomes

| Metric ID | Metric | Baseline | Target | Measurement method |
| --- | --- | --- | --- | --- |
| `MET-01` | Пользователь может самостоятельно собрать корзину в Telegram | Без каталога и корзины бот не решает shopping-задачу | Пользователь проходит путь `/start` → каталог → карточка товара → корзина без участия менеджера | Ручной сценарий и automated tests по handlers/services |
| `MET-02` | Выбор товара не теряется между сессиями | In-memory состояние не подходит для покупательского сценария | Корзина хранится в PostgreSQL и открывается после повторного запуска бота | Интеграционные тесты БД и повторное чтение корзины по `telegram_id` |
| `MET-03` | Каталог достаточно информативен для выбора товара | Текст без структуры и без изображения снижает ценность карточки | Пользователь видит название, цену, описание, характеристики и при наличии `image_url` изображение товара | Acceptance-сценарии каталога и карточки товара |
| `MET-04` | Пользователь доводит shopping flow до заказа внутри Telegram | Каталог и корзина без checkout не закрывают транзакционный сценарий | Пользователь проходит путь `корзина -> телефон -> адрес -> подтверждение -> номер заказа` без ручной дообработки | Handler/integration tests по checkout и order persistence |
| `MET-05` | Order lifecycle прозрачен внутри бота | Заказ без buyer/operator surfaces остаётся opaque | Покупатель видит активные заказы, а `operator`/`admin` управляют статусами и инициируют buyer notification | Handler/service tests по order tracking и operator workflow |

## Constraints

- `PCON-01` Единственная пользовательская поверхность сейчас — Telegram chat UI. Любая feature должна укладываться в модель `message`/`callback_query`, reply keyboard и inline keyboard, а не рассчитывать на web-формы или произвольный layout.
- `PCON-02` Источником истины для пользователей, каталога и корзины является PostgreSQL; данные не должны храниться только в памяти процесса бота.
- `PCON-03` Проект использует асинхронный стек `Aiogram` + `SQLAlchemy async`; новые I/O пути не должны добавлять синхронные блокирующие вызовы в runtime handlers.
- `PCON-04` Текущим поведением системы считаются только сценарии, реализованные в коде и зафиксированные в canonical use-case / feature документации. Roadmap items вроде payment, CRM и непринятых admin extensions нельзя описывать как существующее поведение до их governed closure.

## Source Documents

- [PROJECT.md](../../PROJECT.md) — верхнеуровневое видение продукта и roadmap-направления.
- [README.md](../../README.md) — зафиксированный текущий реализованный scope: каталог, карточка товара с `image_url`, корзина и базовые команды запуска.
- [`../use-cases/UC-001-browse-catalog-and-open-product.md`](../use-cases/UC-001-browse-catalog-and-open-product.md) — канонический сценарий каталога и карточки товара.
- [`../use-cases/UC-002-manage-cart.md`](../use-cases/UC-002-manage-cart.md) — канонический сценарий корзины и сохранения между сессиями.
- [`../use-cases/UC-003-checkout-and-create-order.md`](../use-cases/UC-003-checkout-and-create-order.md) — канонический checkout flow с созданием заказа.
- [`../use-cases/UC-004-check-active-order-status.md`](../use-cases/UC-004-check-active-order-status.md) — buyer-facing просмотр активных заказов.
- [`../use-cases/UC-005-manage-order-status.md`](../use-cases/UC-005-manage-order-status.md) — operator/admin workflow смены статуса заказа.
- [`../use-cases/UC-006-manage-catalog.md`](../use-cases/UC-006-manage-catalog.md) — административное управление категориями и товарами.
- [features/README.md](../features/README.md) — текущее состояние canonical feature packages и ссылка на legacy-архив ранних материалов по каталогу, изображениям и корзине.
- Product-initiative слой уже вынесен в [`../prd/PRD-001-order-lifecycle-and-operations.md`](../prd/PRD-001-order-lifecycle-and-operations.md); отдельных customer research документов для этого репозитория пока нет.
