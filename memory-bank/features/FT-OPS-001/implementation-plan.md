---
title: "FT-OPS-001: Implementation Plan"
doc_kind: feature
doc_function: derived
purpose: "Execution-план реализации operator/admin workflow управления статусами заказов с grounded discovery context, sequencing и verify strategy."
derived_from:
  - feature.md
status: archived
audience: humans_and_agents
must_not_define:
  - ft_ops_001_scope
  - ft_ops_001_architecture
  - ft_ops_001_acceptance_criteria
  - ft_ops_001_blocker_state
---

# План имплементации

## Цель текущего плана

Реализовать role-gated operator/admin vertical slice для работы с заказами: role-aware главное меню, список активных заказов, карточка заказа, update статуса и regression coverage без выхода в role management, уведомления и web backoffice.

## Current State / Reference Points

| Path / module | Current role | Why relevant | Reuse / mirror |
| --- | --- | --- | --- |
| `app/handlers/common/start.py` | `/start` регистрирует/обновляет пользователя и всегда отдает одно и то же главное меню | Здесь появляется role-aware routing по `users.role` | Сохранить pattern `select(User)` + safe DB verdict |
| `app/keyboards/main_menu.py` | Собирает reply keyboard для buyer surface | Нужно превратить в role-aware builder без дублирования меню | Сохранить текущий `get_ui_text(...) -> KeyboardButton(...)` style |
| `app/handlers/order_status.py` | Buyer read-only сценарий просмотра активных заказов | Status mapping должен остаться общим owner-ом для buyer и operator surfaces | Не дублировать mapping статусов в новом handler |
| `app/services/order.py` | Уже умеет создавать заказ и читать active orders текущего buyer | Логичное место для query/update contracts operator slice | Повторить async SQLAlchemy style, commit/rollback discipline и ownership boundary в service |
| `app/services/order_text.py` | Уже форматирует buyer-facing active order list и status labels | Здесь нужно централизовать канонический mapping статусов и добавить operator texts | Расширить единый text-builder вместо второй реализации в handler |
| `app/models/user.py` | Хранит `role`, но оно пока не влияет на поведение | Role gating фичи опирается именно на это поле | Не вводить новые role tables или config |
| `app/models/order.py` | Хранит string status заказа | Status updates идут через существующее поле без schema migration | Поддержать legacy values и новый canonical set в presentation layer |
| `app/callbacks/cart.py` / `app/keyboards/cart.py` | Показывают текущий callback/inline pattern проекта | Новый operator flow должен использовать тот же Telegram contract style | Mirror отдельного callback data class и keyboard builder module |
| `tests/handlers/test_start.py` | Regression на `/start` и главное меню | Нужно доказать, что buyer/operator menu разошлись корректно | Расширить existing integration/unit assertions |
| `tests/handlers/test_order_status.py` | Regression buyer status screen | Даст сигнал, если общий status mapping сломает существующий buyer flow | Использовать как downstream regression surface |
| `tests/test_order_service.py` | Integration coverage order creation и buyer active-list query | Здесь лучше всего добавить update status contract и active-list filtering regression | Расширить existing order service file |
| `tests/test_ui_texts.py` | Unit coverage UI texts и formatting helpers | Подходит для regression на новые labels и builders | Добавить tests рядом с existing status mapping assertions |
| `tests/conftest.py` | Router wiring и DB fixtures | Новый router должен попасть в dispatcher fixture | Следовать include_router pattern и existing DB truncate setup |

## Test Strategy

| Test surface | Canonical refs | Existing coverage | Planned automated coverage | Required local suites / commands | Required CI suites / jobs | Manual-only gap / justification | Manual-only approval ref |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Role-aware `/start` and main menu | `REQ-01`, `EC-01`, `SC-01`, `NEG-01`, `CHK-01`, `CHK-03` | Есть tests только для buyer menu с `Статус заказа` | Обновить `tests/handlers/test_start.py` и `tests/test_ui_texts.py` для `user` vs `operator/admin` меню | `.venv/bin/pytest tests/handlers/test_start.py tests/test_ui_texts.py -v --run-integration` | `none` | `none` | `none` |
| Operator handlers and callbacks | `REQ-02`, `REQ-03`, `REQ-04`, `REQ-05`, `SC-01`, `SC-02`, `SC-03`, `NEG-01`, `CHK-01` | Coverage отсутствует | Добавить `tests/handlers/test_operator_orders.py` на list/detail/update/access-denied/error branches | `.venv/bin/pytest tests/handlers/test_operator_orders.py tests/handlers/test_order_status.py -v --run-integration` | `none` | `none` | `none` |
| Order service query/update contracts | `REQ-03`, `REQ-04`, `EC-03`, `EC-04`, `SC-02`, `SC-03`, `CHK-02` | Есть create-order и buyer active-list coverage | Добавить integration tests на чтение активных заказов для operator slice и смену статуса с terminal-state behavior | `.venv/bin/pytest tests/test_order_service.py -v --run-integration` | `none` | `none` | `none` |
| Shared status mapping and operator text builders | `REQ-03`, `REQ-04`, `EC-04`, `CHK-03` | Есть buyer mapping tests на limited set статусов | Обновить `tests/test_ui_texts.py` на canonical labels, legacy fallback и operator detail/list text | `.venv/bin/pytest tests/test_ui_texts.py -v -m unit` | `none` | `none` | `none` |

## Open Questions / Ambiguities

| Open Question ID | Question | Why unresolved | Blocks | Default action / escalation owner |
| --- | --- | --- | --- | --- |
| `OQ-01` | Как назвать operator entrypoint в reply menu | Upstream docs не фиксируют copy для operator action | `none` | Использовать краткое `Заказы`; если нужен иной product copy, это copy-only follow-up |
| `OQ-02` | Нужно ли ограничивать transition graph, а не просто набор допустимых статусов | PRD требует базовую смену статуса, но не фиксирует жесткие transition rules | `none` | На первой фазе разрешить update в любой канонический статус из списка; если понадобится строгий graph, поднимать upstream feature/ADR |
| `OQ-03` | Нужно ли показывать terminal-state заказ сразу после обновления в detail screen | Scenario требует удалить его из active list, но не задает точный UX после update | `STEP-03` | После update показать обновленную карточку и кнопку возврата; при возврате order исчезает из active list |

## Environment Contract

| Area | Contract | Used by | Failure symptom |
| --- | --- | --- | --- |
| setup | Локальная `.venv` с установленными test dependencies и доступная PostgreSQL из `tests/.env.test` | `STEP-04`, `STEP-05` | Integration tests skip или не стартуют |
| test | Истинным verify считаются зелёные `tests/handlers/test_start.py`, `tests/handlers/test_operator_orders.py`, `tests/test_order_service.py`, `tests/test_ui_texts.py`; для SQLAlchemy surfaces обязателен `--run-integration` | `CHK-01`, `CHK-02`, `CHK-03` | Unit-only verify не закрывает feature |
| access / network / secrets | Live Telegram API, внешние системы и новые секреты не нужны; весь flow реализуется локально | Все шаги | Любая необходимость live credentials считается scope violation |

## Preconditions

| Precondition ID | Canonical ref | Required state | Used by steps | Blocks start |
| --- | --- | --- | --- | --- |
| `PRE-01` | `REQ-01`, `REQ-02`, `REQ-03`, `REQ-04`, `REQ-05` | `feature.md` active и design-ready | `STEP-01`-`STEP-05` | yes |
| `PRE-02` | `ASM-01`, `CTR-03`, `CON-02` | Existing `users.role` and `orders.status` fields достаточно для role gating и status update без schema migration | `STEP-01`, `STEP-02`, `STEP-03` | yes |

## Workstreams

| Workstream | Implements | Result | Owner | Dependencies |
| --- | --- | --- | --- | --- |
| `WS-1` | `REQ-03`, `REQ-04`, `CTR-03`, `CTR-04` | Shared order service/text contracts для operator and buyer surfaces | agent | `PRE-01`, `PRE-02`, `OQ-02` |
| `WS-2` | `REQ-01`, `REQ-02`, `REQ-05`, `CTR-01`, `CTR-02` | Role-aware UI, operator handlers и callback navigation | agent | `WS-1`, `OQ-01`, `OQ-03` |
| `WS-3` | `REQ-06` | Automated coverage, evidence и doc closure | agent | `WS-1`, `WS-2` |

## Approval Gates

| Approval Gate ID | Trigger | Applies to | Why approval is required | Approver / evidence |
| --- | --- | --- | --- | --- |
| `AG-01` | `none` | `none` | Фича не требует live access, schema change или destructive actions вне workspace | `none` |

## Порядок работ

| Step ID | Actor | Implements | Goal | Touchpoints | Artifact | Verifies | Evidence IDs | Check command / procedure | Blocked by | Needs approval | Escalate if |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `STEP-01` | agent | `REQ-03`, `REQ-04`, `CTR-03`, `CTR-04` | Расширить order service и shared text-builder под канонический набор статусов и operator detail/list formatting | `app/services/order.py`, `app/services/order_text.py`, `app/ui_texts.json` | Shared order contracts | `CHK-02`, `CHK-03` | `EVID-02`, `EVID-03` | Integration and unit tests по order/text surfaces | `PRE-01`, `PRE-02`, `OQ-02` | `none` | Если появится потребность в schema migration или строгом transition graph |
| `STEP-02` | agent | `REQ-01`, `REQ-05`, `CTR-01` | Сделать role-aware главное меню и gating по `users.role` | `app/keyboards/main_menu.py`, `app/handlers/common/start.py`, `tests/handlers/test_start.py`, `tests/test_ui_texts.py` | Role-aware entrypoint | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` | Start/UI regression suites | `STEP-01`, `OQ-01` | `none` | Если один builder не покрывает buyer/operator menus без сложного branching |
| `STEP-03` | agent | `REQ-02`, `REQ-03`, `REQ-04`, `REQ-05`, `CTR-02` | Реализовать operator handlers, callbacks и inline keyboards list/detail/update flow | `app/handlers/operator_orders.py`, `app/callbacks/operator_orders.py`, `app/keyboards/operator_orders.py`, `app/main.py`, `tests/conftest.py`, `tests/handlers/test_operator_orders.py` | Operator Telegram workflow | `CHK-01` | `EVID-01` | Handler integration tests | `STEP-01`, `STEP-02`, `OQ-03` | `none` | Если UX потребует pagination/history или другой product-level flow |
| `STEP-04` | agent | `REQ-06` | Расширить order service/UI/buyer regression tests и стабилизировать verify | `tests/test_order_service.py`, `tests/test_ui_texts.py`, `tests/handlers/test_order_status.py`, `tests/handlers/test_operator_orders.py` | Automated coverage | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` | Canonical pytest commands | `STEP-01`, `STEP-02`, `STEP-03` | `none` | Если integration environment недоступен |
| `STEP-05` | agent | `REQ-06` | Собрать evidence, выполнить simplify review и закрыть документацию | `artifacts/ft-ops-001/verify/*`, `memory-bank/features/FT-OPS-001/*`, `memory-bank/use-cases/*`, `memory-bank/prd/PRD-001-order-lifecycle-and-operations.md` | Evidence and final statuses | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` | Verify logs + simplify review pass | `STEP-04` | `none` | Если тесты не стабилизируются после 2-3 итераций |

## Parallelizable Work

- `PAR-01` После стабилизации shared order contracts (`STEP-01`) role-aware start menu и часть unit tests можно делать параллельно с подготовкой operator keyboards.
- `PAR-02` `STEP-01` и `STEP-03` нельзя финализировать независимо, пока не согласован единый status mapping.

## Checkpoints

| Checkpoint ID | Refs | Condition | Evidence IDs |
| --- | --- | --- | --- |
| `CP-01` | `STEP-01`, `CHK-02`, `CHK-03` | Shared status mapping покрывает canonical labels, legacy compatibility и operator formatting | `EVID-02`, `EVID-03` |
| `CP-02` | `STEP-02`, `STEP-03`, `CHK-01` | Role-aware main menu и operator handler workflow проходят list/detail/update/access-denied branches | `EVID-01` |

## Execution Risks

| Risk ID | Risk | Impact | Mitigation | Trigger |
| --- | --- | --- | --- | --- |
| `ER-01` | Status mapping расходится между buyer и operator surfaces | Пользователь и оператор видят разные lifecycle labels | Держать mapping в `app/services/order_text.py` как single owner | Нужно менять статусы в нескольких местах кода |
| `ER-02` | Role gating останется только на UI, но не на callback handlers | Покупатель сможет обойти защиту вручную | Проверять роль и на message entrypoint, и на callback actions | Tests показывают update статуса от `user` |
| `ER-03` | Terminal-state update оставляет заказ в active list | Operator UI противоречит `INV-01` | После update перечитывать active list и проверять filtering integration tests | `completed`/`cancelled` order остается в списке |
| `ER-04` | Integration environment PostgreSQL недоступен | Нельзя доказать critical path | Использовать canonical skip signal и не закрывать feature без реального integration verify | `--run-integration` skip/fail |

## Stop Conditions / Fallback

| Stop ID | Related refs | Trigger | Immediate action | Safe fallback state |
| --- | --- | --- | --- | --- |
| `STOP-01` | `OQ-02`, `ER-01` | Выясняется, что нужен строгий transition graph или новый статусный контракт, не покрытый текущим feature scope | Остановить closure и обновить `feature.md`/PRD before continuing | Фича остается `in_progress` без частично неверного status contract |
| `STOP-02` | `ER-04`, `CHK-01`, `CHK-02` | Нет доступа к working PostgreSQL для integration verify | Не закрывать feature как done; зафиксировать blocking gap | Документы остаются в `in_progress` |

## Готово для приемки

План считается исчерпанным, когда role-aware главное меню, operator list/detail/update flow и shared status mapping реализованы, `CHK-01`/`CHK-02`/`CHK-03` зелёные, evidence сохранено по `EVID-01`/`EVID-02`/`EVID-03`, simplify review пройден и sibling `feature.md` может перейти в `delivery_status: done`.
