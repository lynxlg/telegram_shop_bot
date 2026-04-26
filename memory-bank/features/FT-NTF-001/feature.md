---
title: "FT-NTF-001: Buyer Order Status Notifications"
doc_kind: feature
doc_function: canonical
purpose: "Canonical feature-документ для автоматических Telegram-уведомлений покупателю после смены статуса заказа оператором или администратором."
derived_from:
  - ../../domain/problem.md
  - ../../prd/PRD-001-order-lifecycle-and-operations.md
  - ../../use-cases/UC-004-check-active-order-status.md
  - ../../use-cases/UC-005-manage-order-status.md
  - ../FT-OPS-001/feature.md
  - ../FT-TRK-001/feature.md
status: active
delivery_status: done
audience: humans_and_agents
must_not_define:
  - implementation_sequence
---

# FT-NTF-001: Buyer Order Status Notifications

## What

### Problem

Покупатель уже может вручную открыть экран `Статус заказа`, а оператор уже может менять статус заказа в Telegram. Но между этими двумя slices отсутствует проактивная коммуникация: после operator update покупатель не получает автоматическое подтверждение и должен сам догадываться, что статус изменился.

### Outcome

| Metric ID | Metric | Baseline | Target | Measurement method |
| --- | --- | --- | --- | --- |
| `MET-01` | Buyer получает проактивное подтверждение смены статуса | После operator update уведомление не отправляется | После фактической смены статуса бот отправляет buyer сообщение с номером заказа и новым статусом | Handler tests и service/UI regressions |
| `MET-02` | Notification flow не ломает operator workflow | Любая будущая ошибка доставки рискует прервать handler path, если не изолировать её | Статус в БД сохраняется независимо от результата отправки сообщения | Handler tests на failure path |

### Scope

- `REQ-01` После успешной смены статуса из operator/admin workflow бот отправляет покупателю Telegram-сообщение с номером заказа и человекочитаемым новым статусом.
- `REQ-02` Для текста уведомления используется тот же status mapping, что и в buyer-facing `Статус заказа` и operator UI.
- `REQ-03` Если оператор выбирает тот же статус, который уже сохранен у заказа, уведомление не отправляется.
- `REQ-04` Если отправка уведомления завершается ошибкой Telegram API или transport layer, сохраненный статус заказа не откатывается, а ошибка логируется.
- `REQ-05` Для новой логики добавляется regression coverage на handler-, service- и UI-text surfaces.

### Non-Scope

- `NS-01` Фича не добавляет историю уведомлений, retry queue или отдельную delivery-аудит таблицу.
- `NS-02` Фича не меняет канонический lifecycle статусов и не добавляет новые operator actions.
- `NS-03` Фича не вводит внешние CRM/webhook интеграции, массовые рассылки или маркетинговые коммуникации.

### Constraints / Assumptions

- `ASM-01` Источником истины для статуса заказа остается `orders.status` в PostgreSQL.
- `ASM-02` Buyer notification использует уже существующий `telegram_id` пользователя, связанного с заказом.
- `CON-01` Отправка уведомления происходит только после успешного commit смены статуса.
- `CON-02` Фича сохраняет границу `handlers -> services -> models`; форматирование текста остается централизованным в service presentation layer.
- `INV-01` Одно и то же status label отображается одинаково в buyer list, operator detail и notification message.
- `INV-02` Ошибка отправки уведомления не должна менять verdict operator handler и не должна терять уже сохраненный статус.
- `CTR-01` Service contract смены статуса должен уметь различать фактический transition и no-op update.
- `CTR-02` Notification text contract формируется отдельным text-builder поверх канонического status mapping.
- `FM-01` Buyer notification не отправляется, если статус заказа фактически не изменился.
- `FM-02` Если `bot.send_message` падает, handler логирует ошибку и продолжает штатный ответ оператору.

## How

### Solution

Фича расширяет operator status-update flow дополнительным post-commit шагом. Service слой возвращает не только обновленный заказ, но и признак фактического изменения статуса. Handler после успешного update обновляет operator UI и, только если transition действительно произошел, вызывает отправку buyer notification. Сам текст уведомления формируется в `app/services/order_text.py`, чтобы reuse status mapping оставался единым owner-ом для всех surfaces.

### Change Surface

| Surface | Type | Why it changes |
| --- | --- | --- |
| `app/services/order.py` | code | Service смены статуса должен различать transition и no-op |
| `app/services/order_text.py` | code | Добавляется text-builder buyer notification на базе канонического status mapping |
| `app/handlers/operator_orders.py` | code | Operator status handler отправляет buyer notification после успешного commit и изолирует delivery errors |
| `app/ui_texts.json` | code | Новый copy для статуса уведомления |
| `tests/handlers/test_operator_orders.py` | test | Happy path, no-op path и notification failure path |
| `tests/test_order_service.py` | test | Regression на service result metadata |
| `tests/test_ui_texts.py` | test | Regression на notification text contract |

### Flow

1. Operator/admin открывает карточку заказа и выбирает новый статус.
2. Service обновляет статус в PostgreSQL и сообщает handler, был ли реальный transition.
3. Handler обновляет operator detail screen.
4. Если status transition был фактическим, buyer получает отдельное Telegram-сообщение с номером заказа и новым статусом.
5. Если отправка сообщения падает, ошибка только логируется; operator flow остается успешным.

### Contracts

| Contract ID | Input / Output | Producer / Consumer | Notes |
| --- | --- | --- | --- |
| `CTR-01` | `update_order_status_with_meta(session, order_id, status) -> OrderStatusUpdateResult | None` | `app/services/order.py` / `app/handlers/operator_orders.py` | Возвращает обновленный заказ, предыдущий статус и флаг фактического изменения |
| `CTR-02` | `format_order_status_notification_text(order) -> str` | `app/services/order_text.py` / `app/handlers/operator_orders.py` | Использует тот же status mapping, что и buyer/operator UI |

### Failure Modes

- `FM-01` Operator выбирает статус, равный текущему; service возвращает `changed=False`, buyer notification не отправляется.
- `FM-02` Telegram delivery падает после commit; статус уже сохранен, handler завершает workflow без rollback.

## Verify

### Exit Criteria

- `EC-01` После фактической смены статуса buyer получает сообщение с номером заказа и новым статусом.
- `EC-02` При повторном выборе уже сохраненного статуса buyer notification не отправляется.
- `EC-03` Ошибка отправки уведомления не ломает operator flow и не откатывает обновленный статус.

### Traceability matrix

| Requirement ID | Design refs | Acceptance refs | Checks | Evidence IDs |
| --- | --- | --- | --- | --- |
| `REQ-01` | `ASM-01`, `ASM-02`, `CON-01`, `CTR-01`, `CTR-02` | `EC-01`, `SC-01` | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` |
| `REQ-02` | `CON-02`, `INV-01`, `CTR-02` | `EC-01`, `SC-01` | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` |
| `REQ-03` | `CTR-01`, `FM-01` | `EC-02`, `SC-02` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-04` | `CON-01`, `INV-02`, `FM-02` | `EC-03`, `NEG-01` | `CHK-01` | `EVID-01` |
| `REQ-05` | `CTR-01`, `CTR-02` | `EC-01`, `EC-02`, `EC-03` | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` |

### Acceptance Scenarios

- `SC-01` Operator переводит заказ из `new` в `paid`; статус сохраняется, operator detail screen обновляется, buyer получает сообщение вида `Статус заказа ORD-XXXXXX обновлен: Оплачен.`
- `SC-02` Operator повторно выбирает статус `paid` для уже оплаченного заказа; UI обновляется безопасно, buyer notification не отправляется.

### Negative Coverage

- `NEG-01` `bot.send_message` завершается ошибкой; operator handler завершает workflow без rollback, а status update сохраняется.

### Checks

| Check ID | Covers | How to check | Expected result | Evidence path |
| --- | --- | --- | --- | --- |
| `CHK-01` | `EC-01`, `EC-02`, `EC-03`, `SC-01`, `SC-02`, `NEG-01` | `pytest tests/handlers/test_operator_orders.py -v` | Handler coverage подтверждает happy path, no-op path и notification failure path | `artifacts/ft-ntf-001/verify/chk-01/` |
| `CHK-02` | `EC-02`, `REQ-05` | `pytest tests/test_order_service.py -v` | Service metadata distinguishes changed and unchanged status updates | `artifacts/ft-ntf-001/verify/chk-02/` |
| `CHK-03` | `EC-01`, `REQ-02`, `REQ-05` | `pytest tests/test_ui_texts.py -v -m unit` | Notification text reuses canonical order-status mapping | `artifacts/ft-ntf-001/verify/chk-03/` |

### Test matrix

| Check ID | Evidence IDs | Evidence path |
| --- | --- | --- |
| `CHK-01` | `EVID-01` | `artifacts/ft-ntf-001/verify/chk-01/` |
| `CHK-02` | `EVID-02` | `artifacts/ft-ntf-001/verify/chk-02/` |
| `CHK-03` | `EVID-03` | `artifacts/ft-ntf-001/verify/chk-03/` |

### Evidence

- `EVID-01` Pytest output handler-level verify для status update + buyer notification behavior.
- `EVID-02` Pytest output service-level verify для change/no-op metadata.
- `EVID-03` Pytest output unit verify для notification text contract.

### Evidence contract

| Evidence ID | Artifact | Producer | Path contract | Reused by checks |
| --- | --- | --- | --- | --- |
| `EVID-01` | Текстовый лог pytest handler suite | verify-runner | `artifacts/ft-ntf-001/verify/chk-01/pytest.txt` | `CHK-01` |
| `EVID-02` | Текстовый лог pytest service suite | verify-runner | `artifacts/ft-ntf-001/verify/chk-02/pytest.txt` | `CHK-02` |
| `EVID-03` | Текстовый лог pytest unit suite | verify-runner | `artifacts/ft-ntf-001/verify/chk-03/pytest.txt` | `CHK-03` |
