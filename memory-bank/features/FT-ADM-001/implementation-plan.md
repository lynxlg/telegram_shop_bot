---
title: "FT-ADM-001: Implementation Plan"
doc_kind: feature
doc_function: derived
purpose: "Execution-план реализации FT-ADM-001. Фиксирует discovery context, шаги, риски и test strategy без переопределения canonical feature-фактов."
derived_from:
  - feature.md
status: archived
audience: humans_and_agents
must_not_define:
  - ft_adm_001_scope
  - ft_adm_001_architecture
  - ft_adm_001_acceptance_criteria
  - ft_adm_001_blocker_state
---

# План имплементации

## Цель текущего плана

Реализовать admin-only Telegram workflow управления категориями и товарами каталога: entrypoint в главном меню, навигацию по admin screen-ам, CRUD для категорий и товаров через service layer, FSM для ввода полей и regression coverage без выхода в web backoffice, role management или schema redesign.

## Current State / Reference Points

| Path / module | Current role | Why relevant | Reuse / mirror |
| --- | --- | --- | --- |
| `app/handlers/common/start.py` | Регистрирует пользователя и строит role-aware меню для `operator` | Entry point уже меняется по `users.role`; сюда добавляется admin button | Повторить pattern чтения `User` и передачи `role` в `get_main_menu_keyboard` |
| `app/keyboards/main_menu.py` | Единый builder reply-клавиатуры главного меню | Admin entrypoint должен добавляться здесь, а не отдельным ad-hoc меню | Зеркалить pattern `OPERATOR_ROLES` и conditional row |
| `app/handlers/catalog.py` | Канонический buyer read-only flow по категориям/товарам | Admin workflow не должен ломать catalog navigation и может переиспользовать часть read semantics | Повторить pattern safe `edit_text` / `edit_media`, not-found verdict и role-safe handler structure |
| `app/handlers/operator_orders.py` | Role-gated admin/operator slice с callbacks | Ближайший локальный образец отдельного privileged workflow в Telegram | Повторить `_is_operator`-style access gate, list/detail callbacks и safe error handling |
| `app/handlers/cart.py` | Единственный текущий FSM flow проекта | Admin create/edit сценарии будут опираться на тот же паттерн многошагового ввода | Повторить `StatesGroup`, `FSMContext`, cancel/reset behavior и prompt progression |
| `app/services/catalog.py` | Read-only query contracts buyer каталога | Новые write contracts должны быть рядом, не в handlers | Переиспользовать sorting/query conventions и отдельный service ownership |
| `app/models/category.py`, `app/models/product.py` | Текущая schema категорий и товаров | CRUD опирается на существующие поля и ограничения без миграций | Учитывать `parent_id`, `is_active`, `image_url`, каскады и отсутствие явных uniqueness constraints |
| `app/ui_texts.json` | Единый owner русскоязычного UI copy | Все новые button/prompt/error texts должны появиться здесь | Повторить существующую nested-структуру screen sections |
| `tests/conftest.py` | Общие router fixtures и ORM factories | Новый router и test fixtures должны быть подключены здесь | Переиспользовать `message_factory`, `callback_factory`, `category_factory`, `product_factory` |
| `tests/handlers/test_operator_orders.py` | Локальный паттерн role-gated handler tests | Admin catalog tests должны повторять структуру happy path + denial + db error | Зеркалить unit + integration split |
| `tests/handlers/test_cart.py` | Локальный паттерн тестов FSM handlers | Нужен как reference для state mocks и async assertions | Повторить `AsyncMock`-based `FSMContext` verify |

## Test Strategy

| Test surface | Canonical refs | Existing coverage | Planned automated coverage | Required local suites / commands | Required CI suites / jobs | Manual-only gap / justification | Manual-only approval ref |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Role-aware main menu | `REQ-01`, `SC-01`, `NEG-01`, `CHK-01`, `CHK-03` | Есть coverage для `user` и `operator` menu | Расширить `tests/handlers/test_start.py` и `tests/test_ui_texts.py` на `admin` кнопку и скрытие для остальных ролей | `.venv/bin/pytest tests/handlers/test_start.py tests/test_ui_texts.py -v --run-integration` plus `-m unit` subset | `none` | `none` | `none` |
| Admin handler workflow | `REQ-02`, `REQ-03`, `REQ-04`, `REQ-05`, `REQ-06`, `NEG-01`, `NEG-02`, `CHK-01` | Coverage отсутствует | Добавить `tests/handlers/test_admin_catalog.py` на navigation, create/edit/delete, invalid input и role gating | `.venv/bin/pytest tests/handlers/test_admin_catalog.py -v --run-integration` | `none` | `none` | `none` |
| Catalog admin services | `REQ-03`, `REQ-04`, `REQ-05`, `REQ-06`, `CHK-02` | Есть только read-only catalog service tests | Добавить `tests/test_catalog_admin_service.py` на category/product CRUD и safe delete rules; обновить `tests/test_catalog_service.py` только при необходимости regression на чтение новых данных | `.venv/bin/pytest tests/test_catalog_admin_service.py tests/test_catalog_service.py -v --run-integration` | `none` | `none` | `none` |
| Admin copy / keyboards | `REQ-02`, `REQ-07`, `CHK-03` | Admin surfaces отсутствуют | Добавить unit regression в `tests/test_ui_texts.py` на admin text builders и keyboards | `.venv/bin/pytest tests/test_ui_texts.py -v -m unit` | `none` | `none` | `none` |

## Open Questions / Ambiguities

| Open Question ID | Question | Why unresolved | Blocks | Default action / escalation owner |
| --- | --- | --- | --- | --- |
| `OQ-01` | Как назвать reply entrypoint admin catalog в main menu | Upstream docs не фиксируют copy для admin action | `STEP-01`, `STEP-02` | Использовать краткое `Админ каталог`; если нужен иной copy, это copy-only follow-up |
| `OQ-02` | Нужна ли поддержка `product_attributes` в первом admin CRUD | Scope пользовательской задачи говорит только о категориях и товарах, а в текущей модели attributes живут отдельно | `STEP-04` | Оставить `product_attributes` вне scope по `NS-03`; не добавлять hidden partial editor |
| `OQ-03` | Нужно ли разрешать товары в нелистовой категории | Buyer catalog implicitly treats товары как leaf-category content | `STEP-03`, `STEP-04` | Запретить create product для категорий с дочерними категориями и считать это canonical invariant по `INV-01` |

## Environment Contract

| Area | Contract | Used by | Failure symptom |
| --- | --- | --- | --- |
| setup | Репозиторий использует локальную `.venv` и PostgreSQL test DB из `tests/.env.test` | `STEP-05`, `CHK-01`, `CHK-02`, `CHK-03` | `pytest --run-integration` skip/fail по недоступной БД |
| test | Unit verify идёт через `.venv/bin/pytest ... -m unit`, integration verify через `.venv/bin/pytest ... --run-integration`; integration suites не гонять параллельно | `CHK-01`, `CHK-02`, `CHK-03` | Ложные `deadlock` / `UndefinedTableError` или недостоверный verify |
| access / network / secrets | Фича не требует live Telegram token, внешних API или сетевых разрешений; все проверки детерминируемы локально | Все шаги | Появление зависимости от live media upload или external DB означало бы drift за пределы scope и остановку |

## Preconditions

| Precondition ID | Canonical ref | Required state | Used by steps | Blocks start |
| --- | --- | --- | --- | --- |
| `PRE-01` | `ASM-01`, `CTR-01` | `users.role` уже хранится и используется для role-aware main menu | `STEP-01`, `STEP-02` | yes |
| `PRE-02` | `ASM-02`, `CTR-02` | Проект уже использует Telegram callbacks и FSM как канонический interaction pattern | `STEP-02`, `STEP-03`, `STEP-04` | yes |
| `PRE-03` | `CON-01`, `CTR-03` | Write logic будет заведена в services, а не в handlers | `STEP-03`, `STEP-04` | yes |

## Workstreams

| Workstream | Implements | Result | Owner | Dependencies |
| --- | --- | --- | --- | --- |
| `WS-1` | `REQ-01`, `CTR-01` | Admin-aware main menu и routing entrypoint | agent | `PRE-01` |
| `WS-2` | `REQ-02`, `REQ-03`, `REQ-04`, `CTR-02`, `CTR-04` | Admin category navigation, prompts и category CRUD | agent | `PRE-02`, `WS-1` |
| `WS-3` | `REQ-05`, `REQ-06`, `CTR-03` | Product CRUD services и admin product screens | agent | `PRE-03`, `WS-2`, `OQ-03` |
| `WS-4` | `REQ-07` | Automated regression coverage и evidence | agent | `WS-1`, `WS-2`, `WS-3` |

## Approval Gates

| Approval Gate ID | Trigger | Applies to | Why approval is required | Approver / evidence |
| --- | --- | --- | --- | --- |
| `AG-01` | `none` | `none` | В рамках локальной feature реализация не требует live access, destructive production actions или внешних интеграций | `none` |

## Порядок работ

| Step ID | Actor | Implements | Goal | Touchpoints | Artifact | Verifies | Evidence IDs | Check command / procedure | Blocked by | Needs approval | Escalate if |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `STEP-01` | agent | `REQ-01`, `CTR-01` | Добавить admin entrypoint в main menu и `/start` regression | `app/keyboards/main_menu.py`, `app/ui_texts.json`, `tests/handlers/test_start.py`, `tests/test_ui_texts.py` | Role-aware admin main menu | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` | Targeted pytest for start/menu surfaces | `PRE-01`, `OQ-01` | `none` | Если existing menu contract требует upstream role matrix beyond `admin` |
| `STEP-02` | agent | `REQ-02`, `REQ-03`, `REQ-04`, `CTR-02`, `CTR-04` | Добавить admin callbacks/keyboards/text builders и category navigation / category CRUD handlers | `app/callbacks/admin_catalog.py`, `app/keyboards/admin_catalog.py`, `app/services/admin_catalog_text.py`, `app/handlers/admin_catalog.py`, `app/main.py`, `tests/conftest.py`, `tests/handlers/test_admin_catalog.py`, `tests/test_ui_texts.py` | Admin category workflow | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` | Handler integration tests + unit copy tests | `PRE-02`, `STEP-01` | `none` | Если admin navigation требует richer state model than pragmatic FSM/context approach |
| `STEP-03` | agent | `REQ-03`, `REQ-04`, `REQ-05`, `REQ-06`, `CTR-03` | Реализовать service contracts для category/product CRUD и safe delete rules | `app/services/catalog_admin.py`, `tests/test_catalog_admin_service.py`, `tests/test_catalog_service.py` | Catalog admin write boundary | `CHK-02` | `EVID-02` | Service integration tests | `PRE-03`, `OQ-03` | `none` | Если schema gap потребует migration или change beyond existing fields |
| `STEP-04` | agent | `REQ-05`, `REQ-06`, `FM-02`, `FM-03` | Добавить product create/edit/delete FSM flow и integration with category screens | `app/handlers/admin_catalog.py`, `app/services/catalog_admin.py`, `app/services/admin_catalog_text.py`, `tests/handlers/test_admin_catalog.py` | Admin product workflow | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` | Handler + service integration tests | `STEP-02`, `STEP-03`, `OQ-02` | `none` | Если требование внезапно включает `product_attributes` или multi-media |
| `STEP-05` | agent | `REQ-07` | Прогнать required verify, собрать evidence, выполнить simplify review и обновить feature docs до closure state | `artifacts/ft-adm-001/verify/`, `memory-bank/features/FT-ADM-001/*`, related docs | Evidence set и archived plan | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` | Required pytest commands и doc updates | `STEP-01`, `STEP-02`, `STEP-03`, `STEP-04` | `none` | Если tests нестабильны после 2-3 итераций или среда не даёт достоверный integration verify |

## Parallelizable Work

- `PAR-01` `STEP-01` можно выполнять параллельно с начальной подготовкой service contracts, пока write-surface `app/keyboards/main_menu.py` не пересекается с `app/services/catalog_admin.py`.
- `PAR-02` `STEP-02` и `STEP-03` частично независимы, но integration лучше вести последовательно, потому что handler flow быстро начинает зависеть от точных service contracts.
- `PAR-03` `CHK-01` и `CHK-02` нельзя гонять параллельно из-за общей integration DB и policy на последовательный verify.

## Checkpoints

| Checkpoint ID | Refs | Condition | Evidence IDs |
| --- | --- | --- | --- |
| `CP-01` | `STEP-01`, `CHK-03` | Main menu показывает admin-only entrypoint и не раскрывает его остальным ролям | `EVID-03` |
| `CP-02` | `STEP-02`, `STEP-03`, `CHK-01`, `CHK-02` | Category CRUD и safe delete rules закрыты на code + tests | `EVID-01`, `EVID-02` |
| `CP-03` | `STEP-04`, `STEP-05`, `CHK-01`, `CHK-02`, `CHK-03` | Product CRUD, verify, simplify review и docs closure полностью завершены | `EVID-01`, `EVID-02`, `EVID-03` |

## Execution Risks

| Risk ID | Risk | Impact | Mitigation | Trigger |
| --- | --- | --- | --- | --- |
| `ER-01` | Admin FSM flow быстро разрастается и смешивает category/product branches | Трудно поддерживать handler, повышается риск broken states | Держать state payload минимальным, вынести rendering и write logic в services/text builders | Появление повторяющихся веток с разной ручной сборкой экранов |
| `ER-02` | Delete semantics категории случайно опирается на DB cascades | Потенциально destructive UX и несоответствие `REQ-04` | Явно проверять наличие children/products до delete и покрыть integration test | Category delete проходит без precheck |
| `ER-03` | Role gating дублируется и расходится между text message и callback handlers | Возможен privilege leak | Вынести единый helper проверки admin role в handler slice и покрыть negative tests | Разные handlers начинают проверять роль по-разному |

## Stop Conditions / Fallback

| Stop ID | Related refs | Trigger | Immediate action | Safe fallback state |
| --- | --- | --- | --- | --- |
| `STOP-01` | `CON-02`, `REQ-04`, `ER-02` | Выясняется, что для корректной реализации нужен destructive schema change или migration | Остановить execution, не применять partial destructive logic, поднять вопрос upstream | Оставить admin delete disabled и зафиксировать blocker в feature docs |
| `STOP-02` | `OQ-02`, `NS-03`, `STEP-04` | Появляется требование редактировать `product_attributes` в рамках текущей delivery | Не додумывать scope в коде, вернуть вопрос в canonical feature scope | Завершить только product core fields CRUD |

## Готово для приемки

План считается исчерпанным, когда admin-only main menu, category/product CRUD workflow, safe delete rules, automated regression coverage и evidence реализованы, required pytest suites зелёные, simplify review выполнен, а sibling `feature.md` и связанные governed docs обновлены до closure state.
