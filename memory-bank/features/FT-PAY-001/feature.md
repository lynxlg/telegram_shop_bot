---
title: "FT-PAY-001: Оплата заказов через YooKassa API"
doc_kind: feature
doc_function: canonical
purpose: "Canonical feature-документ для online-оплаты оформленного заказа через YooKassa API с хранением payment attempts и webhook-driven подтверждением оплаты."
derived_from:
  - ../../domain/problem.md
  - ../../domain/architecture.md
  - ../../prd/PRD-001-order-lifecycle-and-operations.md
  - ../../use-cases/UC-003-checkout-and-create-order.md
  - ../../use-cases/UC-005-manage-order-status.md
  - ../../adr/ADR-001-yookassa-webhook-is-payment-source-of-truth.md
status: active
delivery_status: done
audience: humans_and_agents
must_not_define:
  - implementation_sequence
---

# FT-PAY-001: Оплата заказов через YooKassa API

## What

### Problem

Checkout уже создает заказ, но не доводит пользователя до денежной транзакции. Без online payment bot не закрывает основной коммерческий путь, а оператор не видит payment facts для ручной сверки.

### Scope

- `REQ-01` После успешного checkout система создает payment attempt через YooKassa API и отдает пользователю ссылку на оплату.
- `REQ-02` Все payment attempts сохраняются в PostgreSQL вместе с provider payment id, статусом, ссылкой подтверждения и последним provider payload.
- `REQ-03` Заказ получает статус `paid` только после webhook/event `payment.succeeded`.
- `REQ-04` При `payment.canceled` пользователь получает уведомление и может создать новую payment attempt через retry action.
- `REQ-05` В operator UI карточка заказа показывает payment facts последней попытки и счетчик всех попыток.
- `REQ-06` Оператор не может вручную перевести заказ в `paid`; этот переход зарезервирован за payment subsystem.

### Non-Scope

- `NS-01` Фича не добавляет оплату при получении, refund flow или partial captures.
- `NS-02` Фича не строит отдельный web backoffice, invoice history screen или отчетность по платежам.
- `NS-03` Фича не меняет product catalog, pricing rules или lifecycle после статуса `paid` кроме operator guardrails.

### Constraints / Assumptions

- `CON-01` Интеграция использует redirect-flow YooKassa и требует runtime credentials через `Settings`.
- `CON-02` Локальная DB transaction checkout не пересекается с внешним payment API; create-order и create-payment-attempt остаются отдельными шагами.
- `INV-01` `orders.status = paid` может быть выставлен только payment subsystem по событию `payment.succeeded`.
- `INV-02` Каждая новая ссылка на оплату создает или переиспользует отдельную запись `payment_attempts`, а не переписывает историю задним числом.

## How

### Solution

После checkout бот создает локальный заказ и отдельным вызовом создает YooKassa payment, сохраняя результат в `payment_attempts`. Подтверждение оплаты приходит через встроенный HTTP webhook endpoint и только там обновляет заказ до `paid`. Неуспешная оплата не меняет заказ, но запускает retry path для покупателя и делает payment facts видимыми оператору.

### Change Surface

| Surface | Type | Why it changes |
| --- | --- | --- |
| `app/services/payment.py` | code | YooKassa client, persistence payment attempts, retry и webhook processing |
| `app/models/payment_attempt.py` | code | История попыток оплаты |
| `app/webhooks/yookassa.py` | code | HTTP endpoint для provider events |
| `app/handlers/cart.py` | code | Выдача payment link после checkout |
| `app/handlers/payment.py` | code | Buyer retry action |
| `app/handlers/operator_orders.py` | code | Guardrail против ручного `paid` transition |
| `app/services/order_text.py` | code | Payment facts в operator detail view |
| `alembic/versions/20260428_000006_create_payment_attempts_table.py` | data | Новая таблица payment attempts |
| `tests/test_payment_service.py` | test | Integration coverage persistence + webhook status update |
| `tests/handlers/test_payment.py` | test | Retry callback behavior |
| `tests/handlers/test_operator_orders.py` | test | Operator guardrail и payment facts |

### Flow

1. Buyer подтверждает checkout.
2. Система создает заказ и затем payment attempt в YooKassa.
3. Бот отправляет ссылку на оплату.
4. YooKassa отправляет webhook `payment.succeeded` или `payment.canceled`.
5. `payment.succeeded` переводит заказ в `paid`; `payment.canceled` уведомляет пользователя и дает retry action.

## Verify

### Exit Criteria

- `EC-01` После checkout пользователь получает ссылку на оплату, если YooKassa настроена.
- `EC-02` Payment attempts сохраняются в БД и читаются оператором.
- `EC-03` Только webhook `payment.succeeded` переводит заказ в `paid`.
- `EC-04` После `payment.canceled` пользователь может запустить retry flow.

### Acceptance Scenarios

- `SC-01` Пользователь оформляет заказ, получает payment link и видит обычное сообщение об успешном checkout.
- `SC-02` Webhook `payment.succeeded` обновляет payment attempt и переводит заказ в `paid`.
- `SC-03` Webhook `payment.canceled` оставляет заказ неоплаченным, но отправляет пользователю retry action.
- `SC-04` Оператор открывает заказ и видит payment status, payment id, метод и количество попыток.

### Traceability matrix

| Requirement ID | Design refs | Acceptance refs | Checks | Evidence IDs |
| --- | --- | --- | --- | --- |
| `REQ-01` | `CON-01`, `CON-02`, `INV-02` | `EC-01`, `SC-01` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-02` | `CON-02`, `INV-02` | `EC-02`, `SC-02`, `SC-04` | `CHK-02` | `EVID-02` |
| `REQ-03` | `INV-01`, `ADR-001` | `EC-03`, `SC-02` | `CHK-02`, `CHK-03` | `EVID-02`, `EVID-03` |
| `REQ-04` | `INV-02` | `EC-04`, `SC-03` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-05` | `CON-02` | `EC-02`, `SC-04` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-06` | `INV-01`, `ADR-001` | `EC-03`, `SC-04` | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` |

### Checks

| Check ID | Covers | How to check | Expected result | Evidence path |
| --- | --- | --- | --- | --- |
| `CHK-01` | `EC-01`, `EC-02`, `EC-04`, `SC-01`, `SC-03`, `SC-04` | `.venv/bin/pytest tests/handlers/test_cart.py tests/handlers/test_payment.py tests/handlers/test_operator_orders.py -v --run-integration` | Handler-level payment/retry/operator scenarios проходят | `artifacts/ft-pay-001/verify/chk-01/` |
| `CHK-02` | `EC-02`, `EC-03`, `EC-04`, `SC-02`, `SC-03` | `.venv/bin/pytest tests/test_payment_service.py tests/test_database.py tests/test_order_service.py -v --run-integration` | Payment attempt persistence и webhook-driven order update проходят | `artifacts/ft-pay-001/verify/chk-02/` |
| `CHK-03` | `EC-03`, `REQ-06` | `.venv/bin/pytest tests/test_main.py tests/test_ui_texts.py -v -m unit` | Webhook runner wiring и operator/payment UI texts проходят regression | `artifacts/ft-pay-001/verify/chk-03/` |

### Test matrix

| Check ID | Evidence IDs | Evidence path |
| --- | --- | --- |
| `CHK-01` | `EVID-01` | `artifacts/ft-pay-001/verify/chk-01/` |
| `CHK-02` | `EVID-02` | `artifacts/ft-pay-001/verify/chk-02/` |
| `CHK-03` | `EVID-03` | `artifacts/ft-pay-001/verify/chk-03/` |

### Evidence

- `EVID-01` Pytest output handler suites по checkout/payment retry/operator UI.
- `EVID-02` Pytest output integration suites по payment attempts, webhook processing и DB schema.
- `EVID-03` Pytest output unit suites по webhook runner wiring и UI formatting.
