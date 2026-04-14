---
title: "FT-TRK-001: Implementation Plan"
doc_kind: feature
doc_function: derived
purpose: "Execution-план реализации кнопки просмотра статуса активных заказов с grounded discovery context, sequencing и verify strategy."
derived_from:
  - feature.md
status: active
audience: humans_and_agents
must_not_define:
  - ft_trk_001_scope
  - ft_trk_001_architecture
  - ft_trk_001_acceptance_criteria
  - ft_trk_001_blocker_state
---

# План имплементации

## Цель текущего плана

Реализовать read-only vertical slice пользовательского просмотра активных заказов: новая кнопка главного меню, handler, query-service, text formatting и regression coverage без выхода в operator tooling, notifications или историю завершенных заказов.

## Current State / Reference Points

| Path / module | Current role | Why relevant | Reuse / mirror |
| --- | --- | --- | --- |
| `app/keyboards/main_menu.py` | Собирает reply keyboard главного меню с кнопками `Каталог` и `Корзина` | Здесь добавляется новый global entrypoint сценария | Сохранить существующий pattern `get_ui_text(...) -> KeyboardButton(...)` |
| `app/handlers/common/start.py` | `/start` регистрирует пользователя и отдает главное меню | Новая кнопка должна появляться после стартового входа | Не менять user registration path, только reuse `get_main_menu_keyboard()` |
| `app/main.py` | Подключает routers приложения | Новый handler slice должен быть зарегистрирован здесь | Следовать текущему pattern `dispatcher.include_router(...)` |
| `app/models/order.py` | Хранит `order_number`, `status`, `created_at`, `total_amount` | Source of truth для user-facing order status | Schema не менять, использовать existing status string |
| `app/services/order.py` | Реализует checkout-related order creation contract | Здесь логично добавить query-service чтения активных заказов | Сохранить async SQLAlchemy style и rollback/log discipline |
| `app/services/cart_text.py` | Формирует user-facing тексты cart/checkout | Показывает локальный pattern text-builder слоя | Новый order status formatter вынести в отдельный `app/services/order_text.py`, а не собирать строки в handler |
| `app/ui_texts.json` | Canonical store пользовательских строк | Здесь должны жить copy кнопки, empty-state и safe error | Следовать существующей русскоязычной структуре секций |
| `tests/handlers/test_start.py` | Regression на `/start` и главное меню | Нужно доказать появление новой кнопки | Расширить существующие assertions на keyboard |
| `tests/test_order_service.py` | Integration coverage order creation contract | Подходит для query-service активных заказов | Добавить integration tests рядом с существующим order slice |
| `tests/test_ui_texts.py` | Unit verify для keyboard/text builders | Нужен regression на кнопку и status formatter | Следовать existing SimpleNamespace text-builder tests |
| `tests/conftest.py` | Router wiring и DB fixtures | Новый router должен попасть в dispatcher fixture | Повторить existing include_router pattern |

## Test Strategy

| Test surface | Canonical refs | Existing coverage | Planned automated coverage | Required local suites / commands | Required CI suites / jobs | Manual-only gap / justification | Manual-only approval ref |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `app/keyboards/main_menu.py` and `/start` menu | `REQ-01`, `SC-01`, `CHK-01`, `CHK-03` | Есть regression на главное меню, но только для двух кнопок | Обновить start/UI tests для новой кнопки `Статус заказа` | `.venv/bin/pytest tests/handlers/test_start.py tests/test_ui_texts.py -v` | `none` | `none` | `none` |
| `app/handlers/order_status.py` | `REQ-02`, `REQ-03`, `SC-01`, `SC-03`, `NEG-01`, `CHK-01` | Coverage отсутствует | Добавить handler tests на happy path, empty-state и DB error | `.venv/bin/pytest tests/handlers/test_order_status.py -v --run-integration` | `none` | `none` | `none` |
| `app/services/order.py` query-service | `REQ-02`, `REQ-03`, `SC-02`, `SC-03`, `CHK-02` | Есть только create-order coverage | Добавить integration tests на фильтрацию active orders и ownership boundary | `.venv/bin/pytest tests/test_order_service.py -v --run-integration` | `none` | `none` | `none` |
| `app/services/order_text.py` | `REQ-02`, `REQ-03`, `FM-02`, `CHK-03` | Coverage отсутствует | Добавить unit tests на human-readable mapping и fallback copy | `.venv/bin/pytest tests/test_ui_texts.py -v -m unit` | `none` | `none` | `none` |

## Open Questions / Ambiguities

| Open Question ID | Question | Why unresolved | Blocks | Default action / escalation owner |
| --- | --- | --- | --- | --- |
| `OQ-01` | Какие именно статусы считать terminal-state на текущем baseline | В коде пока есть только `new`, а product roadmap перечисляет будущие статусы | `none` | Принять pragmatic terminal set `completed`, `cancelled`; остальные считать active до появления upstream status graph |
| `OQ-02` | Нужно ли показывать детали заказа помимо номера и статуса | User request требует именно просмотр статуса активных заказов, без detail screen | `none` | Ограничить output номером, статусом и краткой подписью; detail/history оставить downstream |

## Environment Contract

| Area | Contract | Used by | Failure symptom |
| --- | --- | --- | --- |
| setup | Локальная `.venv` с установленными test dependencies и доступная PostgreSQL из `tests/.env.test` | `STEP-03`, `STEP-04` | Integration tests skip или не стартуют |
| test | Истинным verify считаются зелёные `tests/handlers/test_start.py`, `tests/handlers/test_order_status.py`, `tests/test_order_service.py`, `tests/test_ui_texts.py`; для SQLAlchemy surfaces обязателен `--run-integration` | `CHK-01`, `CHK-02`, `CHK-03` | Unit-only verify не закрывает feature |
| access / network / secrets | Live Telegram API, внешние системы и новые секреты не нужны; сценарий полностью локальный и read-only относительно orders table | Все шаги | Любая потребность во внешнем API считается scope violation |

## Preconditions

| Precondition ID | Canonical ref | Required state | Used by steps | Blocks start |
| --- | --- | --- | --- | --- |
| `PRE-01` | `REQ-01`, `REQ-02`, `REQ-03` | `feature.md` active и design-ready | `STEP-01`-`STEP-04` | yes |
| `PRE-02` | `ASM-01`, `CON-02`, `CTR-02` | Existing `orders` schema и status string доступны без migration | `STEP-01`, `STEP-02`, `STEP-03` | yes |

## Workstreams

| Workstream | Implements | Result | Owner | Dependencies |
| --- | --- | --- | --- | --- |
| `WS-1` | `REQ-02`, `REQ-03`, `CTR-02`, `CTR-03` | Query-service активных заказов и text formatting статусов | agent | `PRE-01`, `PRE-02`, `OQ-01` |
| `WS-2` | `REQ-01`, `REQ-02`, `REQ-03` | Главное меню и handler entrypoint сценария | agent | `WS-1`, `OQ-02` |
| `WS-3` | `REQ-04` | Automated coverage, evidence и doc closure | agent | `WS-1`, `WS-2` |

## Approval Gates

| Approval Gate ID | Trigger | Applies to | Why approval is required | Approver / evidence |
| --- | --- | --- | --- | --- |
| `AG-01` | `none` | `none` | Фича не требует live access, schema change или destructive actions | `none` |

## Порядок работ

| Step ID | Actor | Implements | Goal | Touchpoints | Artifact | Verifies | Evidence IDs | Check command / procedure | Blocked by | Needs approval | Escalate if |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `STEP-01` | agent | `REQ-02`, `REQ-03` | Добавить query-service чтения активных заказов и formatter статусов | `app/services/order.py`, `app/services/order_text.py`, `app/ui_texts.json` | Read-only order tracking service contracts | `CHK-02`, `CHK-03` | `EVID-02`, `EVID-03` | Integration and unit tests по order slice | `PRE-01`, `PRE-02`, `OQ-01` | `none` | Если status filtering требует upstream product decision beyond pragmatic active/terminal split |
| `STEP-02` | agent | `REQ-01`, `REQ-02`, `REQ-03` | Подключить главное меню и новый handler для текстовой кнопки `Статус заказа` | `app/keyboards/main_menu.py`, `app/handlers/common/start.py`, `app/handlers/order_status.py`, `app/main.py`, `tests/conftest.py` | User-facing entrypoint нового сценария | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` | Handler and UI tests | `STEP-01`, `OQ-02` | `none` | Если сценарий разрастается до detail screen или callback navigation |
| `STEP-03` | agent | `REQ-04` | Добавить и обновить regression tests для handler/service/UI surfaces | `tests/handlers/test_start.py`, `tests/handlers/test_order_status.py`, `tests/test_order_service.py`, `tests/test_ui_texts.py` | Automated coverage feature slice | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` | Canonical pytest commands | `STEP-01`, `STEP-02` | `none` | Если integration environment недоступен |
| `STEP-04` | agent | `REQ-04` | Собрать verify evidence, выполнить simplify review и закрыть документы | `artifacts/ft-trk-001/verify/*`, `memory-bank/features/FT-TRK-001/*`, `memory-bank/use-cases/README.md`, `memory-bank/features/README.md` | Evidence and final statuses | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` | Verify logs + simplify review pass | `STEP-03` | `none` | Если тесты не стабилизируются после 2-3 итераций |

## Parallelizable Work

- `PAR-01` После готовности `STEP-01` handler wiring и часть UI tests можно делать параллельно.
- `PAR-02` `STEP-01` и `STEP-02` нельзя финализировать независимо до стабилизации user-facing text contract.

## Checkpoints

| Checkpoint ID | Refs | Condition | Evidence IDs |
| --- | --- | --- | --- |
| `CP-01` | `STEP-01`, `CHK-02`, `CHK-03` | Query-service фильтрует только активные заказы и formatter стабилен для known/fallback statuses | `EVID-02`, `EVID-03` |
| `CP-02` | `STEP-02`, `STEP-03`, `CHK-01` | Главное меню содержит новую кнопку, handler отдает список/empty-state/error verdict | `EVID-01` |

## Execution Risks

| Risk ID | Risk | Impact | Mitigation | Trigger |
| --- | --- | --- | --- | --- |
| `ER-01` | Status filter слишком рано зафиксирует неверный terminal set | Пользователь не увидит часть нужных заказов или увидит лишние | Ограничить terminal-state только очевидными `completed`, `cancelled` до появления upstream status graph | Integration tests показывают конфликтующий verdict |
| `ER-02` | Text-builder и handler начнут дублировать mapping статусов | Copy расходится между ветками | Держать status mapping в одном presentation helper | Тесты требуют менять одни и те же строки в нескольких местах |
| `ER-03` | Integration environment PostgreSQL недоступен | Нельзя доказать query-service path | Использовать canonical skip signal и не закрывать feature как done без реального integration verify | `--run-integration` skip/fail |

## Stop Conditions / Fallback

| Stop ID | Related refs | Trigger | Immediate action | Safe fallback state |
| --- | --- | --- | --- | --- |
| `STOP-01` | `OQ-01`, `ER-01` | Появляется upstream требование к иному status graph или истории завершенных заказов | Остановить closure и обновить `feature.md`/PRD before continuing | Фича остается в `planned` или `in_progress` без частично неверного контракта |
| `STOP-02` | `ER-03`, `CHK-01`, `CHK-02` | Нет доступа к working PostgreSQL для integration verify | Не закрывать feature как done; зафиксировать blocking gap | Документы остаются в `in_progress` |

## Готово для приемки

План считается исчерпанным, когда новая кнопка доступна после `/start`, handler отдает active order statuses и explicit empty-state, `CHK-01`/`CHK-02`/`CHK-03` зелёные, evidence сохранено по `EVID-01`/`EVID-02`/`EVID-03`, simplify review пройден и sibling `feature.md` может перейти в `delivery_status: done`.
