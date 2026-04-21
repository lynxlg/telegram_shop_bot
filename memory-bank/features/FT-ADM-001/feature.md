---
title: "FT-ADM-001: Admin Catalog Management"
doc_kind: feature
doc_function: canonical
purpose: "Canonical feature-документ для admin workflow создания, изменения и удаления категорий и товаров внутри Telegram-бота."
derived_from:
  - ../../domain/problem.md
  - ../../domain/architecture.md
  - ../../domain/frontend.md
  - ../../prd/PRD-001-order-lifecycle-and-operations.md
  - ../../use-cases/UC-001-browse-catalog-and-open-product.md
  - ../../use-cases/UC-006-manage-catalog.md
status: active
delivery_status: done
audience: humans_and_agents
must_not_define:
  - implementation_sequence
---

# FT-ADM-001: Admin Catalog Management

## What

### Problem

Каталог уже используется покупателем как основной вход в выбор товара, но его состав по-прежнему меняется только через прямую работу с БД. Из-за этого администратор не может безопасно и быстро добавлять новые разделы и товары, корректировать карточки и убирать устаревшие позиции прямо внутри Telegram, а продукт остаётся зависимым от внешнего ручного сопровождения.

### Outcome

| Metric ID | Metric | Baseline | Target | Measurement method |
| --- | --- | --- | --- | --- |
| `MET-01` | Администратор управляет каталогом без прямого доступа к БД | Категории и товары редактируются только вне Telegram | Администратор проходит CRUD-сценарии по категориям и товарам внутри бота | Handler и service tests, acceptance сценарии |
| `MET-02` | Каталог после admin-изменений остаётся совместим с buyer flow | Read-only каталог уже реализован и ценен | Новые и изменённые сущности читаются существующим catalog flow без специальных обходов | Integration tests по services/handlers каталога |
| `MET-03` | Административные действия не раскрываются обычному покупателю | В БД есть `role`, но admin catalog UI отсутствует | Только `admin` видит entrypoint и может пройти CRUD callbacks / FSM steps | Regression tests на access control и main menu |

### Scope

- `REQ-01` Главное меню после `/start` показывает entrypoint управления каталогом только пользователям с ролью `admin`; роли `user` и `operator` этот entrypoint не получают.
- `REQ-02` Администратор может открыть Telegram admin workflow каталога, просмотреть список категорий текущего уровня, перейти в подкатегорию и открыть список товаров выбранной категории.
- `REQ-03` Администратор может создать новую корневую категорию или подкатегорию, а также изменить имя существующей категории.
- `REQ-04` Администратор может удалить категорию только если у неё нет дочерних категорий и товаров; при нарушении этого условия система возвращает безопасный отказ без destructive side effect.
- `REQ-05` Администратор может создать товар в листовой категории и изменить его поля `name`, `price`, `description`, `image_url`, `is_active`.
- `REQ-06` Администратор может удалить товар из категории, а все create/update/delete операции сохраняются в PostgreSQL и сразу отражаются в admin UI.
- `REQ-07` Для admin workflow добавляется deterministic regression coverage на handler-, service-, keyboard- и text-builder surfaces, включая доступ по ролям и negative cases на invalid input.

### Non-Scope

- `NS-01` Фича не вводит web admin panel, bulk import/export, массовое редактирование или отдельный backoffice вне Telegram.
- `NS-02` Фича не управляет ролями пользователей и не меняет правила назначения `admin`.
- `NS-03` Фича не добавляет управление `product_attributes`, остатками, SEO-данными или медиазагрузкой файлов в Telegram.
- `NS-04` Фича не меняет buyer-facing navigation contract каталога кроме чтения уже обновлённых данных.

### Constraints / Assumptions

- `ASM-01` Источником истины для ролей, категорий и товаров остаётся PostgreSQL; для доступа используется `users.role`, для каталога — существующие таблицы `categories`, `products`, `product_attributes`.
- `ASM-02` Admin workflow обязан уложиться в текущий Telegram pattern: reply-кнопка для входа в сценарий, inline-кнопки для навигации и FSM для пошагового ввода полей.
- `CON-01` Фича должна сохранить layered boundary `handlers -> services -> models`; handlers не должны напрямую читать или изменять ORM-сущности вне service contracts.
- `CON-02` Удаление категории должно быть safe-by-default: бот не должен полагаться на каскадное удаление как основной UX для админки.
- `INV-01` Только листовая категория может принимать товары; категория с дочерними категориями не должна одновременно выступать контейнером для новых товаров из admin workflow.
- `INV-02` Неавторизованный доступ к admin flow не должен раскрывать интерфейс управления каталогом и не должен менять данные.
- `CTR-01` Reply keyboard main menu становится contract с отдельным admin entrypoint: `get_main_menu_keyboard(role: str) -> ReplyKeyboardMarkup`.
- `CTR-02` Admin callbacks используют отдельный callback contract для навигации по категориям, выбора товара и CRUD-действий.
- `CTR-03` Catalog admin services становятся единственным write boundary для create/update/delete категорий и товаров.
- `FM-01` Администратор пытается удалить непустую категорию: бот возвращает explicit refusal message и сохраняет категорию без изменений.
- `FM-02` Администратор вводит невалидную цену или обязательное поле пустое: FSM не продвигает сценарий дальше и просит корректный ввод.
- `FM-03` Категория или товар были удалены/изменены между шагами: бот показывает safe not-found verdict и возвращает администратора в устойчивую точку навигации.
- `FM-04` Ошибка БД при create/update/delete: handler логирует контекст и показывает безопасное сообщение без misleading success state.

## How

### Solution

Фича добавляет отдельный admin slice поверх существующего каталога: `/start` строит role-aware меню с entrypoint админки, новый handler открывает иерархию категорий в admin-режиме, а CRUD-операции над категориями и товарами идут через service layer и пошаговый FSM-ввод. Для минимизации риска удаление категорий делается только для пустых узлов, а create/edit product flow ограничивается уже существующими полями модели `Product`.

### Change Surface

| Surface | Type | Why it changes |
| --- | --- | --- |
| `app/handlers/common/start.py` | code | `/start` должен отдавать role-aware main menu с admin entrypoint |
| `app/keyboards/main_menu.py` | code | Главное меню получает admin-only кнопку |
| `app/handlers/admin_catalog.py` | code | Новый handler slice admin CRUD workflow по категориям и товарам |
| `app/callbacks/admin_catalog.py` | code | Новый callback contract admin navigation и CRUD actions |
| `app/keyboards/admin_catalog.py` | code | Inline keyboards списков и карточек admin workflow |
| `app/services/catalog_admin.py` | code | Write contracts категорий и товаров, plus read helpers для admin navigation |
| `app/services/admin_catalog_text.py` | code | Форматирование admin screens и prompts |
| `app/main.py` | code | Подключение нового router |
| `app/ui_texts.json` | code | Новые строки admin UI |
| `tests/handlers/test_start.py` | test | Regression на admin-aware main menu |
| `tests/handlers/test_admin_catalog.py` | test | Handler coverage CRUD, FSM, role gating |
| `tests/test_catalog_admin_service.py` | test | Integration coverage write contracts категорий и товаров |
| `tests/test_ui_texts.py` | test | Regression на main menu и admin text/keyboard builders |
| `tests/conftest.py` | test | Router wiring и reusable fixtures |
| `memory-bank/use-cases/*` | doc | Новый stable admin catalog use case и актуализация индексов |

### Flow

1. Пользователь с ролью `admin` запускает `/start` и видит entrypoint управления каталогом.
2. По entrypoint бот показывает список категорий текущего уровня и действия создания новой категории.
3. Администратор открывает категорию, выбирает нужное действие: создать/изменить/удалить категорию либо перейти к товарам листовой категории.
4. Для create/edit бот проходит пошаговый FSM-ввод и затем вызывает write service.
5. После успешной операции бот возвращает обновлённый admin screen; buyer catalog продолжает читать те же сущности из PostgreSQL.

### Contracts

| Contract ID | Input / Output | Producer / Consumer | Notes |
| --- | --- | --- | --- |
| `CTR-01` | `get_main_menu_keyboard(role: str) -> ReplyKeyboardMarkup` | `app/keyboards/main_menu.py` / `app/handlers/common/start.py` | Единственный keyboard builder главного меню, учитывающий admin entrypoint |
| `CTR-02` | `AdminCatalogCallback(action, category_id, product_id, parent_category_id, field)` | `app/keyboards/admin_catalog.py` / `app/handlers/admin_catalog.py` | Контракт навигации, открытия сущностей и CRUD actions |
| `CTR-03` | `create/update/delete` contracts для категорий и товаров | `app/handlers/admin_catalog.py` / `app/services/catalog_admin.py` | Единственный write boundary admin catalog workflow |
| `CTR-04` | Admin text builders для списков, detail screens и prompts | `app/services/admin_catalog_text.py` / `app/handlers/admin_catalog.py` | Один owner для admin-facing copy и screen assembly |

### Failure Modes

- `FM-01` Непустая категория не может быть удалена; администратор получает явный отказ и остаётся в admin workflow.
- `FM-02` Невалидный ввод поля товара или категории не коммитится и не продвигает FSM дальше.
- `FM-03` Stale `category_id` / `product_id` в callback или FSM context приводит к safe not-found verdict без падения.
- `FM-04` Ошибка БД при чтении или записи каталога приводит к логу с контекстом и безопасному сообщению.

### ADR Dependencies

| ADR | Current `decision_status` | Used for | Execution rule |
| --- | --- | --- | --- |
| `none` | `n/a` | Для локального Telegram admin CRUD отдельный ADR не требуется | Усложнения до media upload, bulk ops или richer permission matrix остаются downstream work |

## Verify

### Exit Criteria

- `EC-01` Пользователь с ролью `admin` после `/start` видит entrypoint admin catalog, а роли `user` и `operator` не видят его.
- `EC-02` Администратор может пройти Telegram workflow по категориям: открыть иерархию, создать категорию, переименовать её и получить обновлённый экран.
- `EC-03` Администратор может создать, изменить и удалить товар в листовой категории; изменения сохраняются в PostgreSQL.
- `EC-04` Удаление непустой категории блокируется безопасным verdict, а удаление пустой категории успешно завершает сценарий.
- `EC-05` Buyer catalog остаётся совместимым с новыми данными каталога, а неавторизованный доступ к admin workflow блокируется.

### Traceability matrix

| Requirement ID | Design refs | Acceptance refs | Checks | Evidence IDs |
| --- | --- | --- | --- | --- |
| `REQ-01` | `ASM-01`, `ASM-02`, `CTR-01`, `INV-02` | `EC-01`, `SC-01`, `NEG-01` | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` |
| `REQ-02` | `ASM-02`, `CTR-02`, `CTR-04`, `FM-03` | `EC-02`, `SC-01` | `CHK-01`, `CHK-03` | `EVID-01`, `EVID-03` |
| `REQ-03` | `ASM-01`, `CON-01`, `CTR-02`, `CTR-03`, `FM-02` | `EC-02`, `SC-02` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-04` | `CON-02`, `CTR-03`, `FM-01` | `EC-04`, `SC-03`, `NEG-02` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-05` | `ASM-01`, `INV-01`, `CTR-03`, `FM-02` | `EC-03`, `SC-02`, `SC-03` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-06` | `ASM-01`, `CTR-03`, `FM-03`, `FM-04` | `EC-03`, `EC-04`, `SC-03` | `CHK-01`, `CHK-02` | `EVID-01`, `EVID-02` |
| `REQ-07` | `CON-01`, `CTR-01`, `CTR-03`, `CTR-04` | `EC-01`, `EC-02`, `EC-03`, `EC-04`, `EC-05` | `CHK-01`, `CHK-02`, `CHK-03` | `EVID-01`, `EVID-02`, `EVID-03` |

### Acceptance Scenarios

- `SC-01` Пользователь с ролью `admin` запускает `/start`, открывает admin catalog, видит корневые категории и может перейти в выбранную категорию без выхода из Telegram.
- `SC-02` Администратор создаёт подкатегорию, затем в листовой категории создаёт товар с именем, ценой, описанием, `image_url` и статусом активности; после завершения бот показывает обновлённый экран, а данные сохраняются в PostgreSQL.
- `SC-03` Администратор изменяет существующий товар, удаляет его, затем удаляет пустую категорию и получает обновлённый admin screen с исчезнувшими сущностями.

### Negative Coverage

- `NEG-01` Пользователь с ролью `user` или `operator` вручную пытается открыть admin flow по тексту или callback, получает safe access-denied verdict, а данные каталога не меняются.
- `NEG-02` Администратор пытается удалить категорию с дочерними категориями или товарами и получает explicit refusal без удаления.

### Checks

| Check ID | Covers | How to check | Expected result | Evidence path |
| --- | --- | --- | --- | --- |
| `CHK-01` | `EC-01`, `EC-02`, `EC-03`, `EC-04`, `EC-05`, `SC-01`, `SC-02`, `SC-03`, `NEG-01`, `NEG-02` | `.venv/bin/pytest tests/handlers/test_start.py tests/handlers/test_admin_catalog.py -v --run-integration` | Main menu, admin handler workflow, FSM input, safe delete rules и role gating проходят deterministic verify | `artifacts/ft-adm-001/verify/chk-01/` |
| `CHK-02` | `EC-02`, `EC-03`, `EC-04`, `REQ-07` | `.venv/bin/pytest tests/test_catalog_admin_service.py tests/test_catalog_service.py -v --run-integration` | Service contracts CRUD по категориям и товарам работают и не ломают read-only catalog queries | `artifacts/ft-adm-001/verify/chk-02/` |
| `CHK-03` | `EC-01`, `EC-02`, `REQ-07` | `.venv/bin/pytest tests/test_ui_texts.py -v -m unit` | Main menu и admin text/keyboard builders проходят regression | `artifacts/ft-adm-001/verify/chk-03/` |

### Test matrix

| Check ID | Evidence IDs | Evidence path |
| --- | --- | --- |
| `CHK-01` | `EVID-01` | `artifacts/ft-adm-001/verify/chk-01/` |
| `CHK-02` | `EVID-02` | `artifacts/ft-adm-001/verify/chk-02/` |
| `CHK-03` | `EVID-03` | `artifacts/ft-adm-001/verify/chk-03/` |

### Evidence

- `EVID-01` Pytest output handler-level verify для admin menu, CRUD workflow и role gating.
- `EVID-02` Pytest output integration verify для write/read service contracts каталога.
- `EVID-03` Pytest output unit verify для main menu, admin text builders и keyboards.

### Evidence contract

| Evidence ID | Artifact | Producer | Path contract | Reused by checks |
| --- | --- | --- | --- | --- |
| `EVID-01` | Текстовый лог pytest handler suite | verify-runner | `artifacts/ft-adm-001/verify/chk-01/pytest.txt` | `CHK-01` |
| `EVID-02` | Текстовый лог pytest integration suite | verify-runner | `artifacts/ft-adm-001/verify/chk-02/pytest.txt` | `CHK-02` |
| `EVID-03` | Текстовый лог pytest unit suite | verify-runner | `artifacts/ft-adm-001/verify/chk-03/pytest.txt` | `CHK-03` |
