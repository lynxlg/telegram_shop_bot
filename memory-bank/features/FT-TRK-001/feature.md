---
title: "FT-TRK-001: View Active Order Status"
doc_kind: feature
doc_function: canonical
purpose: "Canonical feature-документ для кнопки просмотра статуса активных заказов в главном меню Telegram-бота."
derived_from:
  - ../../domain/problem.md
  - ../../domain/architecture.md
  - ../../domain/frontend.md
  - ../../prd/PRD-001-order-lifecycle-and-operations.md
  - ../../use-cases/UC-004-check-active-order-status.md
status: active
delivery_status: in_progress
audience: humans_and_agents
must_not_define:
  - implementation_sequence
---

# FT-TRK-001: View Active Order Status

## What

### Problem

Checkout уже создает заказ, но покупатель не может из главного меню понять, что происходит с его текущими заказами. Из-за этого order lifecycle остается непрозрачным даже после успешного оформления.

### Outcome

| Metric ID | Metric | Baseline | Target | Measurement method |
| --- | --- | --- | --- | --- |
| `MET-01` | Покупатель сам проверяет статус активных заказов | После оформления заказа нет user-facing способа увидеть текущий статус | Пользователь открывает `Статус заказа` и получает список своих активных заказов в Telegram | Handler и service tests, acceptance сценарии |
| `MET-02` | Order status читается без ручной помощи оператора | Order persistence уже существует, но reading flow отсутствует | Система повторно читает активные заказы из PostgreSQL и отдает человекочитаемые статусы | Integration tests по order service |
| `MET-03` | Новый order tracking slice не ломает существующий baseline | Главное меню и checkout уже реализованы | `/start`, главное меню и order creation продолжают работать после добавления новой кнопки и handler | Regression tests по start/menu/order surfaces |

### Scope

- `REQ-01` В главное меню добавляется reply-кнопка `Статус заказа`, доступная обычному покупателю после `/start`.
- `REQ-02` По нажатию кнопки бот читает активные заказы текущего пользователя из PostgreSQL и показывает список с номером заказа и человекочитаемым статусом.
- `REQ-03` Заказы в terminal-state не попадают в список активных; при отсутствии активных заказов бот показывает отдельный понятный verdict.
- `REQ-04` Для нового сценария добавляется deterministic regression coverage на handler-, service- и UI-text surfaces.

### Non-Scope

- `NS-01` Фича не добавляет операторский workflow смены статусов заказа.
- `NS-02` Фича не вводит статусные уведомления, историю завершенных заказов или детальный экран отдельного заказа.
- `NS-03` Фича не меняет schema заказа и не вводит новый status graph beyond current string status storage.

### Constraints / Assumptions

- `ASM-01` Источником истины для заказов остается PostgreSQL и уже существующая таблица `orders`.
- `ASM-02` Новый пользовательский сценарий должен уложиться в существующий Telegram reply-keyboard pattern без web UI и без callback-heavy flow.
- `CON-01` Пользовательские строки и названия статусов остаются русскоязычными и должны продолжать стиль существующего chat UI.
- `CON-02` В БД статус заказа может храниться как техническое строковое значение, поэтому user-facing текст обязан формироваться отдельным presentation-layer mapping.
- `INV-01` Чтение статусов заказа не должно менять заказ, корзину или профиль пользователя.
- `CTR-01` Reply keyboard главного меню расширяется кнопкой `Статус заказа`, а handler по текстовой кнопке возвращает один итоговый ответ.
- `CTR-02` Query contract `get_active_orders_by_telegram_id(session, telegram_id) -> list[Order]` является единственной service entrypoint для чтения активных заказов пользователя.
- `FM-01` У пользователя нет активных заказов: бот возвращает explicit empty-state сообщение.
- `FM-02` Заказ содержит статус, которого нет в известном mapping: бот показывает безопасное fallback-название статуса вместо падения.
- `FM-03` Чтение заказов завершается `SQLAlchemyError`: handler логирует ошибку и показывает безопасное сообщение.

## How

### Solution

Фича добавляет новый read-only order tracking slice: главное меню получает кнопку `Статус заказа`, новый handler вызывает query-service чтения активных заказов пользователя, а отдельный text-builder преобразует order numbers и internal statuses в компактный Telegram-ответ. Это сохраняет архитектурную границу `handlers -> services -> models` и не требует изменения существующей order schema.

### Change Surface

| Surface | Type | Why it changes |
| --- | --- | --- |
| `app/keyboards/main_menu.py` | code | Добавление новой глобальной reply-кнопки пользовательского сценария |
| `app/handlers/common/start.py` | code | `/start` должен отдавать обновленное главное меню |
| `app/handlers/order_status.py` | code | Новый handler slice для запуска сценария просмотра статусов |
| `app/main.py` | code | Подключение нового router |
| `app/services/order.py` | code | Query-service чтения активных заказов пользователя |
| `app/services/order_text.py` | code | Форматирование списка заказов и mapping статусов для Telegram UI |
| `app/ui_texts.json` | code | Новые пользовательские строки и copy для main menu / order status |
| `tests/handlers/test_start.py` | test | Regression на главное меню после `/start` |
| `tests/handlers/test_order_status.py` | test | Handler coverage нового сценария |
| `tests/test_order_service.py` | test | Integration coverage query-service по активным заказам |
| `tests/test_ui_texts.py` | test | Regression на новый copy и text builders |
| `tests/conftest.py` | test | Router wiring для handler tests |

### Flow

1. Пользователь нажимает `Статус заказа` в главном меню.
2. Handler читает активные заказы текущего пользователя через service.
3. Text-builder формирует compact list `номер заказа -> статус`.
4. Бот возвращает список активных заказов, empty-state или безопасное сообщение об ошибке.

### Contracts

| Contract ID | Input / Output | Producer / Consumer | Notes |
| --- | --- | --- | --- |
| `CTR-01` | reply button `Статус заказа` | `app/keyboards/main_menu.py` / `app/handlers/order_status.py` | Новый глобальный entrypoint пользовательского сценария |
| `CTR-02` | `get_active_orders_by_telegram_id(session, telegram_id) -> list[Order]` | `app/services/order.py` / `app/handlers/order_status.py` | Возвращает только active orders текущего пользователя |
| `CTR-03` | `format_active_orders_text(orders) -> str` | `app/services/order_text.py` / `app/handlers/order_status.py` | User-facing formatting и status mapping из internal string в русский verdict |

### Failure Modes

- `FM-01` У пользователя нет активных заказов; handler показывает empty-state, а не пустой список.
- `FM-02` В БД встречается незнакомое значение статуса; text-builder показывает безопасный fallback.
- `FM-03` Ошибка БД при чтении заказов; handler показывает безопасную ошибку и не раскрывает технические детали.

### ADR Dependencies

| ADR | Current `decision_status` | Used for | Execution rule |
| --- | --- | --- | --- |
| `none` | `n/a` | Для read-only user flow отдельный ADR не требуется | Любое усложнение до истории, notifications или operator status management остается downstream-feature |

## Verify

### Exit Criteria

- `EC-01` Пользователь после `/start` видит кнопку `Статус заказа` в главном меню.
- `EC-02` Пользователь с активными заказами получает список своих заказов с номером и человекочитаемым статусом.
- `EC-03` Пользователь без активных заказов получает explicit empty-state, а terminal-state заказы не попадают в список.

### Traceability matrix

| Requirement ID | Design refs | Acceptance refs | Checks | Evidence IDs |
| --- | --- | --- | --- | --- |
| `REQ-01` | `ASM-02`, `CON-01`, `CTR-01` | `EC-01`, `SC-01` | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` |
| `REQ-02` | `ASM-01`, `CON-01`, `CON-02`, `CTR-02`, `CTR-03`, `FM-02` | `EC-02`, `SC-01`, `SC-02` | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` |
| `REQ-03` | `ASM-01`, `INV-01`, `CTR-02`, `FM-01`, `FM-03` | `EC-03`, `SC-03`, `NEG-01` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-04` | `ASM-01`, `ASM-02` | `EC-01`, `EC-02`, `EC-03` | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` |

### Acceptance Scenarios

- `SC-01` Пользователь после `/start` нажимает `Статус заказа` и получает список из нескольких активных заказов с корректными номерами и русскими статусами.
- `SC-02` Один из активных заказов хранится со статусом `new`, и пользователь видит человекочитаемый статус `Принят`.
- `SC-03` Пользователь без активных заказов получает сообщение об их отсутствии; завершенные и отмененные заказы в список не попадают.

### Negative Coverage

- `NEG-01` При инфраструктурной ошибке чтения заказов бот показывает безопасное сообщение об ошибке и не раскрывает текст исключения.

### Checks

| Check ID | Covers | How to check | Expected result | Evidence path |
| --- | --- | --- | --- | --- |
| `CHK-01` | `EC-01`, `EC-02`, `EC-03`, `SC-01`, `SC-03`, `NEG-01` | `.venv/bin/pytest tests/handlers/test_start.py tests/handlers/test_order_status.py -v --run-integration` | Главное меню и handler сценария order status проходят happy-path и guarding cases | `artifacts/ft-trk-001/verify/chk-01/` |
| `CHK-02` | `EC-02`, `EC-03`, `SC-02`, `SC-03` | `.venv/bin/pytest tests/test_order_service.py -v --run-integration` | Query-service возвращает только активные заказы текущего пользователя и исключает terminal-state | `artifacts/ft-trk-001/verify/chk-02/` |
| `CHK-03` | `EC-01`, `EC-02`, `REQ-04` | `.venv/bin/pytest tests/test_ui_texts.py -v -m unit` | UI texts, main menu keyboard и text-builder order status проходят regression | `artifacts/ft-trk-001/verify/chk-03/` |

### Test matrix

| Check ID | Evidence IDs | Evidence path |
| --- | --- | --- |
| `CHK-01` | `EVID-01` | `artifacts/ft-trk-001/verify/chk-01/` |
| `CHK-02` | `EVID-02` | `artifacts/ft-trk-001/verify/chk-02/` |
| `CHK-03` | `EVID-03` | `artifacts/ft-trk-001/verify/chk-03/` |

### Evidence

- `EVID-01` Pytest output handler-level verify для main menu и order status flow.
- `EVID-02` Pytest output integration verify для query-service активных заказов.
- `EVID-03` Pytest output unit verify для UI texts и order status formatting.

### Evidence contract

| Evidence ID | Artifact | Producer | Path contract | Reused by checks |
| --- | --- | --- | --- | --- |
| `EVID-01` | Текстовый лог pytest handler suite | verify-runner | `artifacts/ft-trk-001/verify/chk-01/pytest.txt` | `CHK-01` |
| `EVID-02` | Текстовый лог pytest integration suite | verify-runner | `artifacts/ft-trk-001/verify/chk-02/pytest.txt` | `CHK-02` |
| `EVID-03` | Текстовый лог pytest unit suite | verify-runner | `artifacts/ft-trk-001/verify/chk-03/pytest.txt` | `CHK-03` |
