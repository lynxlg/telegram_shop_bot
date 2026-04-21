---
title: "FT-OPS-001: Operator Order Status Management"
doc_kind: feature
doc_function: canonical
purpose: "Canonical feature-документ для operator/admin workflow просмотра активных заказов и смены их статусов в Telegram."
derived_from:
  - ../../domain/problem.md
  - ../../domain/architecture.md
  - ../../domain/frontend.md
  - ../../prd/PRD-001-order-lifecycle-and-operations.md
  - ../../use-cases/UC-004-check-active-order-status.md
  - ../../use-cases/UC-005-manage-order-status.md
status: active
delivery_status: done
audience: humans_and_agents
must_not_define:
  - implementation_sequence
---

# FT-OPS-001: Operator Order Status Management

## What

### Problem

Checkout уже создает заказы, а buyer flow уже читает их статусы, но у оператора и администратора нет встроенного Telegram-контура, в котором можно открыть активные заказы и перевести их по каноническому lifecycle. Из-за этого order lifecycle остаётся partially manual и buyer-facing статусный контур не может считаться управляемым внутри продукта.

### Outcome

| Metric ID | Metric | Baseline | Target | Measurement method |
| --- | --- | --- | --- | --- |
| `MET-01` | Оператор обрабатывает заказ внутри Telegram | После создания заказа статусы нельзя менять через бот | Оператор открывает активные заказы, выбирает заказ и меняет его статус без внешнего интерфейса | Handler и service tests, acceptance сценарии |
| `MET-02` | Статусный lifecycle канонизирован для read/write surfaces | Сейчас status storage string-based и не управляется role-gated workflow | Для operator flow и buyer tracking используется один набор допустимых статусов и одинаковый user-facing mapping | Integration tests по service + unit tests по text mapping |
| `MET-03` | Operator tooling не открывается обычному покупателю | `role` хранится в БД, но не влияет на UI и handlers | Только `operator` и `admin` видят вход в workflow и проходят callback paths | Handler tests на access control и start/menu regression |
| `MET-04` | Новый operator slice не ломает checkout и buyer order tracking | Заказы уже создаются и читаются пользователем | Checkout, buyer status screen и `/start` продолжают работать после добавления operator workflow | Regression tests по start/order/cart surfaces |

### Scope

- `REQ-01` Главное меню после `/start` показывает operator entrypoint только пользователям с ролью `operator` или `admin`; пользователи с ролью `user` не получают этот entrypoint.
- `REQ-02` Operator/admin по entrypoint получает список активных заказов с возможностью открыть карточку конкретного заказа внутри Telegram.
- `REQ-03` Карточка заказа показывает номер, текущий статус, покупателя, телефон, адрес и inline-действия для смены статуса в одном каноническом наборе: `Создан`, `Оплачен`, `Собран`, `Передан в доставку`, `Получен`, `Отменен`.
- `REQ-04` Смена статуса сохраняется в PostgreSQL и немедленно отражается в operator UI и buyer-facing text mapping.
- `REQ-05` Любой доступ к operator flow и callback actions со стороны роли `user` блокируется безопасным verdict без изменения заказа.
- `REQ-06` Для operator workflow и обновленного status mapping добавляется deterministic regression coverage на handler-, service-, keyboard- и text-builder surfaces.

### Non-Scope

- `NS-01` Фича не вводит web admin panel, отдельный backoffice, pagination или расширенный OMS workflow.
- `NS-02` Фича не управляет ролями пользователей и не описывает процесс назначения `operator`/`admin`.
- `NS-03` Фича не отправляет buyer notifications и не интегрируется с CRM, платежами или доставкой.
- `NS-04` Фича не меняет checkout fields, order schema shape или историю завершенных заказов beyond status update behavior.

### Constraints / Assumptions

- `ASM-01` Источником истины для ролей и заказов остаётся PostgreSQL; роль пользователя читается из `users.role`, статус заказа хранится в `orders.status`.
- `ASM-02` Operator/admin UI обязан уложиться в существующий Telegram pattern: reply-кнопка для входа в сценарий и inline-кнопки для действий над сущностью.
- `CON-01` Фича должна сохранить layered boundary `handlers -> services -> models`; handlers не должны менять статус заказа прямым SQL.
- `CON-02` Для обратной совместимости buyer-facing surfaces обязаны продолжать читать legacy status values, если они уже встречаются в БД.
- `INV-01` Terminal-state заказы `completed` и `cancelled` не должны возвращаться в operator active list после успешного обновления.
- `INV-02` Попытка неавторизованного доступа не меняет UI для покупателя на operator workflow и не обновляет `orders.status`.
- `CTR-01` Reply keyboard main menu становится role-aware contract: `get_main_menu_keyboard(role: str) -> ReplyKeyboardMarkup`.
- `CTR-02` Operator callbacks используют отдельный callback contract для открытия заказа, возврата к списку и обновления статуса.
- `CTR-03` Service contract `update_order_status(session, order_id, status) -> Order | None` является единственной write entrypoint смены статуса заказа.
- `CTR-04` Status presentation contract централизован в `app/services/order_text.py` и используется и buyer, и operator surfaces.
- `FM-01` У operator/admin нет активных заказов: бот показывает explicit empty-state вместо пустой клавиатуры.
- `FM-02` Неавторизованный пользователь вручную отправляет operator button text или callback payload: система показывает access-denied verdict и не раскрывает admin UI.
- `FM-03` В БД встречается legacy или неизвестный статус: text-builder и operator detail screen показывают safe fallback label вместо падения.
- `FM-04` Обновление статуса завершается `SQLAlchemyError`: handler логирует ошибку, не показывает технические детали и не оставляет misleading success state.

## How

### Solution

Фича добавляет отдельный operator slice поверх уже существующей order persistence: `/start` строит role-aware главное меню, новый handler открывает список активных заказов и карточку выбранного заказа, а order service получает write-contract для смены статуса. Status mapping централизуется в одном text-builder слое, чтобы buyer tracking и operator UI читали одинаковый lifecycle без дублирования правил по handlers.

### Change Surface

| Surface | Type | Why it changes |
| --- | --- | --- |
| `app/handlers/common/start.py` | code | `/start` должен отдавать role-aware main menu |
| `app/keyboards/main_menu.py` | code | Главное меню становится role-aware и получает operator entrypoint |
| `app/handlers/operator_orders.py` | code | Новый handler slice operator/admin workflow |
| `app/callbacks/operator_orders.py` | code | Новый callback contract выбора заказа и смены статуса |
| `app/keyboards/operator_orders.py` | code | Inline keyboards списка заказов и карточки заказа |
| `app/main.py` | code | Подключение нового router |
| `app/services/order.py` | code | Query/update contracts для operator active list и status change |
| `app/services/order_text.py` | code | Канонический mapping статусов и форматирование operator screens |
| `app/ui_texts.json` | code | Новые строки operator UI и обновленный status copy |
| `tests/handlers/test_start.py` | test | Regression на role-aware main menu |
| `tests/handlers/test_operator_orders.py` | test | Handler coverage operator flow и access control |
| `tests/test_order_service.py` | test | Integration coverage status update contracts |
| `tests/test_ui_texts.py` | test | Regression на status mapping и operator keyboard/text builders |
| `tests/conftest.py` | test | Router wiring нового handler slice |
| `memory-bank/use-cases/*` | doc | Новый stable operator use case и актуализация индексов |

### Flow

1. Пользователь с ролью `operator` или `admin` запускает `/start` и видит reply-кнопку управления заказами.
2. По нажатию entrypoint handler читает активные заказы и показывает список с inline-кнопками выбора заказа.
3. Operator открывает карточку заказа и нажимает одну из канонических кнопок статуса.
4. Handler вызывает service смены статуса, перечитывает заказ и обновляет текущий Telegram-экран.
5. После перевода заказа в terminal-state он исчезает из списка активных заказов; buyer-facing status mapping продолжает показывать обновленное значение.

### Contracts

| Contract ID | Input / Output | Producer / Consumer | Notes |
| --- | --- | --- | --- |
| `CTR-01` | `get_main_menu_keyboard(role: str) -> ReplyKeyboardMarkup` | `app/keyboards/main_menu.py` / `app/handlers/common/start.py` | Единственный keyboard builder главного меню, учитывающий роли |
| `CTR-02` | `OperatorOrdersCallback(action, order_id, status)` | `app/keyboards/operator_orders.py` / `app/handlers/operator_orders.py` | Контракт выбора order list item, возврата и update action |
| `CTR-03` | `update_order_status(session, order_id, status) -> Order | None` | `app/handlers/operator_orders.py` / `app/services/order.py` | Write boundary смены статуса с commit/refresh semantics |
| `CTR-04` | `format_operator_order_list_text(orders)` / `format_operator_order_details_text(order)` / `format_order_status(status)` | `app/services/order_text.py` / operator and buyer handlers | Один owner для human-readable lifecycle |

### Failure Modes

- `FM-01` У operator/admin нет активных заказов; handler возвращает explicit empty-state и не рисует пустую inline-клавиатуру.
- `FM-02` Пользователь без нужной роли вызывает operator text button или callback; handler возвращает access-denied verdict и не меняет заказ.
- `FM-03` Order id отсутствует или уже ушел из active set; handler показывает безопасное сообщение и предлагает вернуться к списку.
- `FM-04` Ошибка БД при чтении или обновлении заказа; handler логирует контекст и показывает безопасное сообщение.

### ADR Dependencies

| ADR | Current `decision_status` | Used for | Execution rule |
| --- | --- | --- | --- |
| `none` | `n/a` | Для локального role-gated Telegram workflow отдельный ADR не требуется | Любое усложнение до matrix permissions, уведомлений или external ops orchestration остается downstream-feature |

## Verify

### Exit Criteria

- `EC-01` Пользователь с ролью `operator` или `admin` после `/start` видит operator entrypoint, а пользователь с ролью `user` не видит его.
- `EC-02` Operator/admin может открыть активные заказы и карточку конкретного заказа внутри Telegram.
- `EC-03` Operator/admin может сменить статус заказа на любой из канонических вариантов, и новое значение сохраняется в PostgreSQL.
- `EC-04` Buyer-facing order status mapping и operator UI используют одинаковые названия статусов, включая fallback для legacy/unknown values.
- `EC-05` Неавторизованный доступ к operator flow блокируется без изменения заказа.

### Traceability matrix

| Requirement ID | Design refs | Acceptance refs | Checks | Evidence IDs |
| --- | --- | --- | --- | --- |
| `REQ-01` | `ASM-01`, `ASM-02`, `CTR-01`, `FM-02` | `EC-01`, `SC-01`, `NEG-01` | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` |
| `REQ-02` | `ASM-02`, `CTR-02`, `FM-01`, `FM-03` | `EC-02`, `SC-01`, `SC-02` | `CHK-01` | `EVID-01` |
| `REQ-03` | `ASM-01`, `CON-01`, `CTR-02`, `CTR-03`, `CTR-04`, `FM-03` | `EC-03`, `SC-02`, `SC-03` | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` |
| `REQ-04` | `ASM-01`, `CTR-03`, `CTR-04`, `INV-01`, `FM-04` | `EC-03`, `EC-04`, `SC-03` | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` |
| `REQ-05` | `ASM-01`, `INV-02`, `FM-02` | `EC-05`, `NEG-01` | `CHK-01` | `EVID-01` |
| `REQ-06` | `CON-01`, `CTR-03`, `CTR-04` | `EC-01`, `EC-02`, `EC-03`, `EC-04`, `EC-05` | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` |

### Acceptance Scenarios

- `SC-01` Пользователь с ролью `operator` после `/start` нажимает entrypoint заказов и получает список нескольких активных заказов с inline-кнопками выбора.
- `SC-02` Operator открывает карточку заказа со статусом `new` и видит канонический русскоязычный статус `Создан`, затем переводит заказ в `paid` и видит обновленный экран.
- `SC-03` Operator переводит заказ в `completed` или `cancelled`; статус сохраняется, detail screen обновляется, а после возврата заказ больше не попадает в active list.

### Negative Coverage

- `NEG-01` Пользователь с ролью `user` вручную пытается открыть operator flow по тексту или callback, получает safe access-denied verdict, а статус заказа не меняется.

### Checks

| Check ID | Covers | How to check | Expected result | Evidence path |
| --- | --- | --- | --- | --- |
| `CHK-01` | `EC-01`, `EC-02`, `EC-03`, `EC-05`, `SC-01`, `SC-02`, `SC-03`, `NEG-01` | `.venv/bin/pytest tests/handlers/test_start.py tests/handlers/test_operator_orders.py -v --run-integration` | Role-aware start menu и operator handler workflow проходят happy-path, terminal-state update и access control | `artifacts/ft-ops-001/verify/chk-01/` |
| `CHK-02` | `EC-03`, `EC-04`, `SC-02`, `SC-03` | `.venv/bin/pytest tests/test_order_service.py -v --run-integration` | Query/update contracts заказов сохраняют статус, исключают terminal-state и не ломают buyer ownership boundaries | `artifacts/ft-ops-001/verify/chk-02/` |
| `CHK-03` | `EC-01`, `EC-04`, `REQ-06` | `.venv/bin/pytest tests/test_ui_texts.py -v -m unit` | Main menu, status mapping и operator text/keyboard builders проходят regression | `artifacts/ft-ops-001/verify/chk-03/` |

### Test matrix

| Check ID | Evidence IDs | Evidence path |
| --- | --- | --- |
| `CHK-01` | `EVID-01` | `artifacts/ft-ops-001/verify/chk-01/` |
| `CHK-02` | `EVID-02` | `artifacts/ft-ops-001/verify/chk-02/` |
| `CHK-03` | `EVID-03` | `artifacts/ft-ops-001/verify/chk-03/` |

### Evidence

- `EVID-01` Pytest output handler-level verify для role-aware start menu и operator workflow.
- `EVID-02` Pytest output integration verify для query/update contracts заказов.
- `EVID-03` Pytest output unit verify для main menu, status mapping и operator text builders.

### Evidence contract

| Evidence ID | Artifact | Producer | Path contract | Reused by checks |
| --- | --- | --- | --- | --- |
| `EVID-01` | Текстовый лог pytest handler suite | verify-runner | `artifacts/ft-ops-001/verify/chk-01/pytest.txt` | `CHK-01` |
| `EVID-02` | Текстовый лог pytest integration suite | verify-runner | `artifacts/ft-ops-001/verify/chk-02/pytest.txt` | `CHK-02` |
| `EVID-03` | Текстовый лог pytest unit suite | verify-runner | `artifacts/ft-ops-001/verify/chk-03/pytest.txt` | `CHK-03` |
