---
title: "FT-ORD-001: Implementation Plan"
doc_kind: feature
doc_function: derived
purpose: "Execution-план реализации checkout из корзины с grounded discovery context, sequencing и verify strategy."
derived_from:
  - feature.md
status: archived
audience: humans_and_agents
must_not_define:
  - ft_ord_001_scope
  - ft_ord_001_architecture
  - ft_ord_001_acceptance_criteria
  - ft_ord_001_blocker_state
---

# План имплементации

## Цель текущего плана

Реализовать vertical slice оформления заказа из корзины: Telegram checkout flow, order persistence, cart cleanup semantics и regression coverage без выхода за границы оплаты, трекинга статусов и operator tooling.

## Current State / Reference Points

| Path / module | Current role | Why relevant | Reuse / mirror |
| --- | --- | --- | --- |
| `app/handlers/cart.py` | Открывает корзину и обрабатывает inline-действия `+/-/Удалить` | Основная entrypoint поверхность checkout | Сохранить pattern `service -> safe user verdict` и обновление текущего экрана |
| `app/keyboards/cart.py` | Inline keyboard для позиций корзины | Здесь добавляется запуск checkout и confirm/cancel actions | Расширить существующий builder без поломки item actions |
| `app/callbacks/cart.py` | Canonical callback schema корзины | Нужно расширить action contract | Сохранить единый `CartCallback` prefix |
| `app/services/cart.py` | Работа с корзиной и commit/rollback patterns | Reuse чтения корзины и safe DB behavior | Повторить logging/rollback discipline |
| `app/services/cart_text.py` | Формирует текст корзины | Нужен для summary и total reuse | Добавить checkout summary рядом с cart formatting |
| `app/models/user.py` | User aggregate с опциональным `phone` | Reuse сохранённого телефона и связь пользователя с заказами | Не вводить отдельный профильный storage |
| `app/models/database.py` | Bootstrap импортирует модели и создает schema | Новые order-модели должны регистрироваться здесь | Следовать текущему metadata-init pattern |
| `tests/handlers/test_cart.py` | Handler regression pattern с `message_factory`/`callback_factory` | Основная verify surface для UI flow | Следовать existing SimpleNamespace/AsyncMock style |
| `tests/test_cart_service.py` | Integration coverage корзины | Нужно доказать cleanup semantics и отсутствие регрессии cart baseline | Расширить существующий integration файл там, где логика пересекается |
| `tests/conftest.py` | Test DB bootstrap, router wiring, factories | Нужен для новых routers/models/table cleanup | Расширить truncate list и dispatcher wiring |

## Test Strategy

| Test surface | Canonical refs | Existing coverage | Planned automated coverage | Required local suites / commands | Required CI suites / jobs | Manual-only gap / justification | Manual-only approval ref |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `app/handlers/cart.py` checkout flow | `REQ-01`, `REQ-02`, `REQ-04`, `SC-01`, `SC-02`, `NEG-01`, `NEG-02`, `CHK-01` | Есть coverage только для открытия корзины и item actions | Добавить integration-style handler tests на start/phone/address/confirm/cancel/error branches | `.venv/bin/pytest tests/handlers/test_cart.py -v --run-integration` | `none` | `none` | `none` |
| `app/services/order.py` и order schema | `REQ-03`, `REQ-04`, `SC-01`, `SC-02`, `NEG-03`, `CHK-02` | Coverage отсутствует | Добавить integration tests на order creation, item snapshot, unique number, cart cleanup rollback-safe semantics | `.venv/bin/pytest tests/test_order_service.py tests/test_cart_service.py tests/test_database.py -v --run-integration` | `none` | `none` | `none` |
| Cart baseline regression | `REQ-04`, `REQ-05`, `SC-01`, `NEG-03`, `CHK-02` | Есть tests на add/increase/decrease/remove | Обновить существующие tests, чтобы order changes не ломали cart persistence | `.venv/bin/pytest tests/test_cart_service.py tests/handlers/test_cart.py -v --run-integration` | `none` | `none` | `none` |

## Open Questions / Ambiguities

| Open Question ID | Question | Why unresolved | Blocks | Default action / escalation owner |
| --- | --- | --- | --- | --- |
| `OQ-01` | Нужен ли отдельный persisted checkout draft state или достаточно in-memory FSM state | Upstream scope требует только локальный Telegram checkout до confirm и не требует cross-session draft restore | `none` | Реализовать ephemeral FSM state внутри бота; если понадобится persistence между сессиями, поднимать новую feature |
| `OQ-02` | Нужна ли специальная маска валидации телефона | Product docs требуют сбор контакта, но не задают строгий E.164 contract | `none` | Принять pragmatic validation: непустое значение достаточной длины, поддержка contact share и plain text |

## Environment Contract

| Area | Contract | Used by | Failure symptom |
| --- | --- | --- | --- |
| setup | Локальная `.venv` с установленными test dependencies и доступная PostgreSQL из `tests/.env.test` | `STEP-04`, `STEP-05` | Integration tests skip или не стартуют |
| test | Истинным verify считаются только зелёные `--run-integration` suites для handler/service/schema change surface | `CHK-01`, `CHK-02` | Unit-only verify недостаточен для closure |
| access / network / secrets | Live Telegram API и внешние сервисы не нужны; работа полностью локальная | Все шаги | Любая попытка вынести flow во внешний сервис считается scope violation |

## Preconditions

| Precondition ID | Canonical ref | Required state | Used by steps | Blocks start |
| --- | --- | --- | --- | --- |
| `PRE-01` | `REQ-01`, `REQ-02`, `REQ-03`, `REQ-04` | `feature.md` active и design-ready | `STEP-01`-`STEP-05` | yes |
| `PRE-02` | `DEC-01`, `CON-02` | Checkout ограничен локальной DB transaction без payment/integration side effects | `STEP-02`, `STEP-03` | yes |

## Workstreams

| Workstream | Implements | Result | Owner | Dependencies |
| --- | --- | --- | --- | --- |
| `WS-1` | `REQ-03`, `REQ-04` | Order models, migration, service contract создания заказа | agent | `PRE-01`, `PRE-02` |
| `WS-2` | `REQ-01`, `REQ-02`, `REQ-04` | Telegram checkout flow и UX around cart screen | agent | `WS-1` |
| `WS-3` | `REQ-05` | Automated regression coverage и evidence | agent | `WS-1`, `WS-2` |

## Approval Gates

| Approval Gate ID | Trigger | Applies to | Why approval is required | Approver / evidence |
| --- | --- | --- | --- | --- |
| `AG-01` | `none` | `none` | В рамках локальной feature реализация не требует live access, destructive production actions или внешних интеграций | `none` |

## Порядок работ

| Step ID | Actor | Implements | Goal | Touchpoints | Artifact | Verifies | Evidence IDs | Check command / procedure | Blocked by | Needs approval | Escalate if |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `STEP-01` | agent | `REQ-03` | Добавить order domain model и schema для хранения заказа и order items | `app/models/order.py`, `app/models/order_item.py`, `app/models/user.py`, `app/models/database.py`, `alembic/versions/*` | Order schema and ORM wiring | `CHK-02` | `EVID-02` | Integration tests на schema и persistence | `PRE-01`, `PRE-02` | `none` | Если schema требует новый upstream contract вне `feature.md` |
| `STEP-02` | agent | `REQ-03`, `REQ-04` | Реализовать service создания заказа из текущей корзины и cleanup semantics | `app/services/order.py`, `app/services/cart.py`, `app/services/cart_text.py` | Transactional service contract | `CHK-02` | `EVID-02` | Service/integration tests | `STEP-01`, `OQ-02` | `none` | Если локальная transaction не покрывает observed consistency risk |
| `STEP-03` | agent | `REQ-01`, `REQ-02`, `REQ-04` | Добавить многошаговый checkout flow в handlers/keyboards/callbacks | `app/handlers/cart.py`, `app/keyboards/cart.py`, `app/callbacks/cart.py`, `app/main.py`, `tests/conftest.py` | User-facing checkout flow | `CHK-01` | `EVID-01` | Handler tests | `STEP-02`, `OQ-01` | `none` | Если UX требует новый product-level сценарий вне `UC-003` |
| `STEP-04` | agent | `REQ-05` | Обновить и добавить regression tests для service, database и handlers | `tests/test_order_service.py`, `tests/test_cart_service.py`, `tests/test_database.py`, `tests/handlers/test_cart.py` | Automated coverage | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` | Canonical pytest commands | `STEP-01`, `STEP-02`, `STEP-03` | `none` | Если integration environment недоступен |
| `STEP-05` | agent | `REQ-05` | Собрать verify evidence, выполнить simplify review и закрыть feature docs | `artifacts/ft-ord-001/verify/*`, `memory-bank/features/FT-ORD-001/*` | Evidence and final statuses | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` | Verify logs + review pass | `STEP-04` | `none` | Если тесты не стабилизируются после 2-3 итераций |

## Parallelizable Work

- `PAR-01` После готовности schema (`STEP-01`) часть service-тестов и handler wiring можно готовить параллельно.
- `PAR-02` `STEP-02` и `STEP-03` нельзя финализировать независимо до стабилизации callback и service contract.

## Checkpoints

| Checkpoint ID | Refs | Condition | Evidence IDs |
| --- | --- | --- | --- |
| `CP-01` | `STEP-01`, `STEP-02` | Order schema создана, service умеет создать заказ и очистить корзину после commit | `EVID-02` |
| `CP-02` | `STEP-03`, `STEP-04` | Handler flow проходит happy path и negative branches | `EVID-01` |

## Execution Risks

| Risk ID | Risk | Impact | Mitigation | Trigger |
| --- | --- | --- | --- | --- |
| `ER-01` | FSM flow конфликтует с существующими cart callbacks и message handlers | Checkout UX работает нестабильно | Изолировать state по user и держать checkout entrypoints в cart slice | Handler tests на cancel/confirm/message branches падают |
| `ER-02` | Order creation partially commits without cart cleanup | Нарушается `INV-01` | Держать order creation и cart cleanup внутри одной transaction | После create_order корзина всё ещё содержит позиции |
| `ER-03` | Integration environment PostgreSQL недоступен | Нельзя доказать critical path | Использовать canonical skip signal и не закрывать feature без реального integration verify | `--run-integration` skip/fail |

## Stop Conditions / Fallback

| Stop ID | Related refs | Trigger | Immediate action | Safe fallback state |
| --- | --- | --- | --- | --- |
| `STOP-01` | `DEC-01`, `ER-02` | Выясняется, что локальная transaction не обеспечивает безопасный create+cleanup path | Остановить feature closure и поднять вопрос в ADR/upstream design | Код остается без partially rolled feature |
| `STOP-02` | `ER-03`, `CHK-01`, `CHK-02` | Нет доступа к working PostgreSQL для integration verify | Не закрывать feature как done; зафиксировать blocking gap | Документы остаются в `in_progress` |

## Готово для приемки

План считается исчерпанным, когда order schema, checkout flow и regression coverage реализованы, `CHK-01` и `CHK-02` зелёные, evidence сохранено по `EVID-01`/`EVID-02`, simplify review пройден и sibling `feature.md` может перейти в `delivery_status: done`.
