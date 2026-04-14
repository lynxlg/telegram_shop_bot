---
title: "FT-ORD-001: Checkout From Cart"
doc_kind: feature
doc_function: canonical
purpose: "Canonical feature-документ для оформления заказа из корзины со сбором контактов, подтверждением и созданием заказа в PostgreSQL."
derived_from:
  - ../../domain/problem.md
  - ../../domain/architecture.md
  - ../../domain/frontend.md
  - ../../prd/PRD-001-order-lifecycle-and-operations.md
  - ../../use-cases/UC-003-checkout-and-create-order.md
status: active
delivery_status: done
audience: humans_and_agents
must_not_define:
  - implementation_sequence
---

# FT-ORD-001: Checkout From Cart

## What

### Problem

Проект уже доводит покупателя до заполненной корзины, но не закрывает обязательный следующий шаг: пользователь не может передать контакты, подтвердить заказ и получить номер заказа внутри Telegram. Из-за этого shopping flow обрывается между выбором товаров и фиксацией заказа.

### Outcome

| Metric ID | Metric | Baseline | Target | Measurement method |
| --- | --- | --- | --- | --- |
| `MET-01` | Пользователь завершает checkout внутри Telegram | Корзина не переводится в заказ | Пользователь проходит `Корзина -> телефон -> адрес -> подтверждение -> созданный заказ` без выхода из бота | Handler/integration tests и acceptance сценарий |
| `MET-02` | Заказ сохраняется как отдельная сущность | Отдельной сущности заказа нет | После подтверждения появляется заказ с номером, контактами, адресом, итоговой суммой и позициями | Integration tests с чтением БД |
| `MET-03` | Корзина не теряется до подтверждения | Checkout отсутствует | До успешного подтверждения корзина не очищается, после успешного подтверждения очищается | Acceptance и negative coverage |

### Scope

- `REQ-01` Пользователь из непустой корзины может запустить checkout и пройти пошаговый сбор телефона и адреса в Telegram.
- `REQ-02` Бот показывает перед созданием заказа сводку с составом корзины, суммой, телефоном и адресом и требует явного подтверждения.
- `REQ-03` После подтверждения система атомарно создает заказ в PostgreSQL с уникальным номером, снапшотом контактных данных, адресом, итоговой суммой и позициями корзины.
- `REQ-04` После успешного создания заказа корзина очищается; при отмене или ошибке создания корзина остается неизменной.
- `REQ-05` Для checkout добавляется deterministic regression coverage на service- и handler-level.

### Non-Scope

- `NS-01` Фича не реализует онлайн-оплату, оплату при получении и payment status.
- `NS-02` Фича не реализует просмотр истории заказов, трекинг статуса заказа и уведомления.
- `NS-03` Фича не добавляет операторский или административный workflow работы с заказами.

### Constraints / Assumptions

- `ASM-01` Источником истины остаётся PostgreSQL, а checkout реализуется внутри существующего стека `Aiogram` + `SQLAlchemy async`.
- `ASM-02` Текущий UX-паттерн проекта допускает многошаговый Telegram flow через короткие сообщения и inline/reply keyboard без web-форм.
- `CON-01` Пользовательские тексты и кнопки должны оставаться на русском языке и следовать существующему chat UI стилю.
- `CON-02` До появления отдельного payment flow заказ создается в базовом статусе без внешних side effects.
- `DEC-01` Для этой delivery-единицы checkout фиксируется как локальная DB transaction без row-level locking и без внешних API; допустимый baseline — один подтвержденный заказ на один explicit confirm action.
- `INV-01` Корзина не очищается до успешного `commit` заказа.
- `INV-02` Состав заказа после создания является снапшотом корзины на момент подтверждения и не зависит от будущих изменений каталога или корзины.

## How

### Solution

Checkout добавляется как отдельный Telegram flow поверх существующей корзины: handler переводит пользователя в короткую последовательность `телефон -> адрес -> подтверждение`, а service в одном транзакционном вызове создает заказ и позиции заказа из текущей корзины, затем очищает корзину. Это сохраняет existing cart baseline и ограничивает новый critical write path одним локальным DB commit.

### Change Surface

| Surface | Type | Why it changes |
| --- | --- | --- |
| `app/handlers/cart.py` | code | Точка входа в корзину и новый checkout UI flow |
| `app/keyboards/cart.py` | code | Кнопка запуска checkout и действия подтверждения/отмены |
| `app/callbacks/cart.py` | code | Новый callback contract для checkout actions |
| `app/services/cart.py` | code | Повторное использование чтения корзины и очистки после заказа |
| `app/services/cart_text.py` | code | Текстовые builders корзины и сводки checkout |
| `app/services/order.py` | code | Создание заказа, позиций и номера заказа |
| `app/models/order.py` | code | Order aggregate root |
| `app/models/order_item.py` | code | Snapshot позиций заказа |
| `app/models/user.py` | code | Связь пользователя с заказами и reuse phone |
| `app/models/database.py` | code | Регистрация новых моделей в bootstrap |
| `alembic/versions/*` | data | Создание таблиц заказов |
| `tests/handlers/test_cart.py` | test | Handler regression coverage checkout flow |
| `tests/test_cart_service.py` | test | Regression на сохранение/очистку корзины |
| `tests/test_order_service.py` | test | Integration coverage order creation contract |

### Flow

1. Пользователь открывает непустую корзину и нажимает `Оформить заказ`.
2. Бот запрашивает телефон, затем адрес, сохраняя промежуточный checkout state на время диалога.
3. После ввода данных бот показывает сводку заказа и inline-кнопки подтверждения или отмены.
4. При подтверждении service перечитывает корзину, создает заказ и позиции, очищает корзину и возвращает номер заказа.
5. Бот показывает сообщение об успешном создании заказа; при отмене или ошибке возвращает пользователя в безопасное состояние без очистки корзины.

### Contracts

| Contract ID | Input / Output | Producer / Consumer | Notes |
| --- | --- | --- | --- |
| `CTR-01` | `cart:checkout` / `cart:confirm_order` / `cart:cancel_checkout` callback actions | `app/keyboards/cart.py` / `app/handlers/cart.py` | Расширяет существующий callback contract корзины без изменения каталога |
| `CTR-02` | `create_order_from_cart(session, telegram_id, phone, address) -> Order` | `app/handlers/cart.py` / `app/services/order.py` | Один service-вход для атомарного создания заказа |
| `CTR-03` | `orders` и `order_items` schema | `app/models/*`, Alembic / `app/services/order.py` | Хранит order number, user, phone, address, total и snapshot позиций |

### Failure Modes

- `FM-01` Пользователь пытается начать checkout с пустой корзиной. Система не открывает flow и показывает `Корзина пуста.`
- `FM-02` Пользователь отправляет невалидный телефон или пустой адрес. Система повторно запрашивает корректное значение и не продвигается к подтверждению.
- `FM-03` За время checkout корзина очищена или изменилась так, что заказ создать нельзя. Service возвращает безопасный отказ без очистки и без фиктивного номера.
- `FM-04` DB ошибка во время создания заказа. Транзакция откатывается, корзина сохраняется, пользователь получает безопасное сообщение об ошибке.

### ADR Dependencies

| ADR | Current `decision_status` | Used for | Execution rule |
| --- | --- | --- | --- |
| `none` | `n/a` | Для этой фичи отдельный ADR не создается; concurrency baseline зафиксирован в `DEC-01` | Любое требование к row-level locking, payment side effects или multi-step orchestration вне локальной БД считается out of scope |

## Verify

### Exit Criteria

- `EC-01` Пользователь может пройти happy path checkout из непустой корзины до сообщения с номером заказа.
- `EC-02` Подтвержденный заказ сохраняется в PostgreSQL вместе с позициями, адресом, телефоном и итоговой суммой.
- `EC-03` Корзина очищается только после успешного создания заказа и не очищается при отмене или ошибке.

### Traceability matrix

| Requirement ID | Design refs | Acceptance refs | Checks | Evidence IDs |
| --- | --- | --- | --- | --- |
| `REQ-01` | `ASM-01`, `ASM-02`, `CON-01`, `CTR-01`, `FM-01`, `FM-02` | `EC-01`, `SC-01`, `SC-02`, `NEG-01` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-02` | `CON-01`, `CTR-01`, `FM-02` | `EC-01`, `SC-01` | `CHK-01` | `EVID-01` |
| `REQ-03` | `ASM-01`, `CON-02`, `DEC-01`, `INV-02`, `CTR-02`, `CTR-03`, `FM-03`, `FM-04` | `EC-02`, `SC-01`, `SC-02` | `CHK-02` | `EVID-02` |
| `REQ-04` | `DEC-01`, `INV-01`, `INV-02`, `FM-03`, `FM-04` | `EC-03`, `SC-01`, `SC-02`, `NEG-02`, `NEG-03` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-05` | `ASM-01`, `DEC-01` | `EC-01`, `EC-02`, `EC-03` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |

### Acceptance Scenarios

- `SC-01` Пользователь с непустой корзиной проходит шаги ввода телефона и адреса, подтверждает заказ и получает сообщение с номером заказа; в БД сохранены заказ и позиции, корзина очищена.
- `SC-02` Пользователь запускает checkout с уже сохраненным телефоном, меняет адрес, подтверждает заказ и получает корректную сводку с новым адресом и итоговой суммой.

### Checks

| Check ID | Covers | How to check | Expected result | Evidence path |
| --- | --- | --- | --- | --- |
| `CHK-01` | `EC-01`, `EC-03`, `SC-01`, `SC-02`, `NEG-01`, `NEG-02` | `.venv/bin/pytest tests/handlers/test_cart.py -v --run-integration` | Handler-level checkout scenarios и guarding cases проходят | `artifacts/ft-ord-001/verify/chk-01/` |
| `CHK-02` | `EC-02`, `EC-03`, `SC-01`, `SC-02`, `NEG-03` | `.venv/bin/pytest tests/test_order_service.py tests/test_cart_service.py tests/test_database.py -v --run-integration` | Order persistence, snapshot contract и cart cleanup regression проходят | `artifacts/ft-ord-001/verify/chk-02/` |

### Test matrix

| Check ID | Evidence IDs | Evidence path |
| --- | --- | --- |
| `CHK-01` | `EVID-01` | `artifacts/ft-ord-001/verify/chk-01/` |
| `CHK-02` | `EVID-02` | `artifacts/ft-ord-001/verify/chk-02/` |

### Evidence

- `EVID-01` Pytest output handler-level checkout verify.
- `EVID-02` Pytest output integration verify for order persistence and cart cleanup.

### Evidence contract

| Evidence ID | Artifact | Producer | Path contract | Reused by checks |
| --- | --- | --- | --- | --- |
| `EVID-01` | Текстовый лог pytest handler suite | verify-runner | `artifacts/ft-ord-001/verify/chk-01/pytest.txt` | `CHK-01` |
| `EVID-02` | Текстовый лог pytest integration suites | verify-runner | `artifacts/ft-ord-001/verify/chk-02/pytest.txt` | `CHK-02` |
