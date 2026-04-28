---
title: "ADR-001-yookassa-webhook-is-payment-source-of-truth"
doc_kind: adr
doc_function: canonical
purpose: "Фиксирует источник истины для статуса оплаты заказа и границу между локальной БД и внешним YooKassa API."
derived_from:
  - ../domain/architecture.md
  - ../prd/PRD-001-order-lifecycle-and-operations.md
status: active
decision_status: accepted
audience: humans_and_agents
---

# ADR-001: YooKassa webhook is payment source of truth

## Context

Проект добавляет онлайн-оплату заказов через YooKassa. Это первый flow, где локальная БД и внешний платежный API участвуют в одном пользовательском сценарии. Требование issue `FT-PAY-001` задает два критичных инварианта:

- заказ получает статус `paid` только после подтвержденного события `payment.succeeded`;
- система хранит отдельные payment attempts и позволяет повторить оплату после `payment.canceled`.

Текущая архитектура проекта не допускает общий "best effort" блок, где один transaction одновременно изменяет PostgreSQL и вызывает внешний API.

## Decision

Принять следующие правила:

1. Checkout сначала атомарно создает локальный заказ в PostgreSQL, а платежная попытка создается отдельным шагом после `commit`.
2. Источником истины для перехода заказа в `paid` считается только webhook/event `payment.succeeded` от YooKassa.
3. Операторский UI не может вручную переводить заказ из `new` в `paid`; он только видит payment facts и продолжает lifecycle после подтвержденной оплаты.
4. Каждая новая ссылка на оплату сохраняется как отдельная запись `payment_attempts`.
5. `payment.canceled` обновляет последнюю попытку и инициирует buyer-facing retry path, но не меняет `orders.status`.

## Consequences

### Positive

- Payment state и order state расходятся только контролируемо и объяснимо.
- Повторные попытки оплаты и ручная сверка имеют исторический след в БД.
- Проект не нарушает архитектурную границу между локальной транзакцией и внешним API.

### Trade-offs

- У приложения появляется дополнительный runtime surface: HTTP webhook endpoint.
- Между созданием заказа и подтверждением оплаты появляется явный промежуточный unpaid-state.
- Тестовый контур обязан покрывать отдельно checkout, payment attempt persistence и webhook-driven status update.
