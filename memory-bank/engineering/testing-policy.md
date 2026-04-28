---
title: Testing Policy
doc_kind: engineering
doc_function: canonical
purpose: Описывает testing policy репозитория: обязательность test case design, требования к automated regression coverage и допустимые manual-only gaps.
derived_from:
  - ../dna/governance.md
  - ../flows/feature-flow.md
status: active
canonical_for:
  - repository_testing_policy
  - feature_test_case_inventory_rules
  - automated_test_requirements
  - sufficient_test_coverage_definition
  - manual_only_verification_exceptions
  - simplify_review_discipline
  - verification_context_separation
must_not_define:
  - feature_acceptance_criteria
  - feature_scope
audience: humans_and_agents
---

# Testing Policy

## Core Rules

- Любое изменение поведения, которое можно проверить детерминированно, обязано получить automated regression coverage.
- Любой новый или измененный contract обязан получить contract-level automated verification.
- Любой bugfix обязан добавить regression test на воспроизводимый сценарий.
- Required automated tests считаются закрывающими риск только если они проходят локально и в CI.
- Manual-only verify допустим только как явное исключение и не заменяет automated coverage там, где automation реалистична.

## Ownership Split

- Canonical test cases delivery-единицы задаются в `feature.md` через `SC-*`, feature-specific `NEG-*`, `CHK-*` и `EVID-*`.
- `implementation-plan.md` владеет только стратегией исполнения: какие test surfaces будут добавлены или обновлены, какие gaps временно остаются manual-only и почему.

## Feature Flow Expectations

Canonical lifecycle gates живут в [../flows/feature-flow.md](../flows/feature-flow.md):

- к `Design Ready` `feature.md` уже фиксирует test case inventory;
- к `Plan Ready` `implementation-plan.md` содержит `Test Strategy` с planned automated coverage и manual-only gaps;
- к `Done` required tests добавлены, локальные команды зелёные и CI не противоречит локальному verify.

## Что Считается Sufficient Coverage

- Покрыт основной changed behavior и ближайший regression path.
- Покрыты новые или измененные contracts, события, schema или integration boundaries.
- Покрыты критичные failure modes из `FM-*`, bug history или acceptance risks.
- Покрыты feature-specific negative/edge scenarios, если они меняют verdict.
- Процент line coverage сам по себе недостаточен: нужен scenario- и contract-level coverage.

## Когда Manual-Only Допустим

- Сценарий зависит от live infra, внешних систем, hardware, недетерминированной среды или human оценки UI.
- Для каждого manual-only gap: причина, ручная процедура, owner follow-up.
- Если manual-only gap оставляет без regression protection критичный путь, feature не считается завершённой.

## Simplify Review

Отдельный проход верификации после функционального тестирования. Цель: убедиться, что реализация минимально сложна.

- Выполняется после прохождения tests, но до closure gate.
- Паттерны: premature abstractions, глубокая вложенность, дублирование логики, dead code, overengineering.
- Три похожие строки лучше premature abstraction. Абстракция оправдана только когда она реально уменьшает риск или повтор.

## Verification Context Separation

Разные этапы верификации — отдельные проходы:

1. **Функциональная верификация** — tests проходят, acceptance scenarios покрыты
2. **Simplify review** — код минимально сложен
3. **Acceptance test** — end-to-end по `SC-*`

Для small features допустимо в одной сессии, но simplify review не пропускается.

## Project-Specific Conventions

- **Framework:** `pytest` + `pytest-asyncio`. Все тесты живут в `tests/`, async-сценарии помечаются `@pytest.mark.asyncio`.
- **Test split:** проект использует два режима. `unit` ставится автоматически для тестов без integration fixtures; `integration` ставится для тестов, использующих `db_session`, `test_engine` или `test_session_factory`.
- **Canonical local commands:**
  - Python format перед lint/test: `.venv/bin/ruff format .`
  - Python lint перед тестами: `.venv/bin/ruff check .`
  - быстрый smoke для Python-приложения: `.venv/bin/pytest tests/ -v -m unit`
  - полный прогон приложения с PostgreSQL: `.venv/bin/pytest tests/ -v --run-integration`
  - прогон с coverage: `./scripts/run-tests.sh`
  - bootstrap/CLI smoke: `./scripts/test-ci.sh` и `./scripts/test-setup.sh` относятся к окружению репозитория, а не заменяют app-level verify
- **Sequencing rule:** если используется full verify path вроде `./scripts/run-tests.sh`, сначала выполняются `ruff format` и `ruff check`, и только потом `pytest`, чтобы formatting/style/import issues останавливали verify до более дорогих тестов.
- **Test data pattern:** базовый reusable setup живёт в [tests/conftest.py](/home/lynx/telegram_shop_bot/tests/conftest.py). Для Telegram объектов и ORM-сущностей используй существующие factory fixtures (`message_factory`, `callback_factory`, `category_factory`, `product_factory`) вместо дублирования hand-made setup в каждом тесте.
- **Database strategy:** integration tests поднимают отдельную PostgreSQL БД на основе `tests/.env.test`, создают schema через `Base.metadata.create_all`, а между тестами очищают таблицы через `TRUNCATE ... RESTART IDENTITY CASCADE`. Если сценарий требует реальный SQLAlchemy session lifecycle или persistence between sessions, он должен идти через integration path, а не через моки.
- **Docker reality for this repo:** canonical local PostgreSQL из `docker-compose.yml` слушает `localhost:55432`, тогда как `tests/.env.test` по умолчанию может смотреть на `localhost:5432`. Если integration verify выполняется именно через Docker PostgreSQL, агент должен синхронизировать test DSN на время прогона и вернуть его назад после verify; подробная процедура зафиксирована в [../ops/runbooks/postgres-integration-tests.md](../ops/runbooks/postgres-integration-tests.md).
- **PostgreSQL preflight:** перед `pytest --run-integration` агент обязан проверить, какой runtime используется для БД verify: локальная PostgreSQL на `5432`, Docker PostgreSQL на `55432` или другой эквивалентный forward. Нельзя молча запускать integration suite против неподтверждённого DSN и затем трактовать skip как feature verdict.
- **Sandbox boundary:** в агентской sandbox-среде локальные сокеты `asyncpg` могут быть запрещены даже при доступном Docker-контейнере. Если `pytest --run-integration` skip/fail-ится из-за socket permissions, canonical следующий шаг — повторить тот же integration прогон вне sandbox, а не объявлять feature manual-only.
- **Skip interpretation:** массовые `integration tests skipped`, `Не удалось создать отдельную тестовую БД PostgreSQL`, `PermissionError` или socket-open ошибки на `--run-integration` в этом проекте считаются environment signal, а не доказанным регрессом в коде. Такой результат требует environment correction и повторного PostgreSQL verify.
- **Sequencing rule for evidence:** integration pytest-команды, которые используют общую test DB `shop_bot_test`, нельзя гонять параллельно. Иначе teardown fixture может словить DDL/TRUNCATE race и выдать ложные `deadlock detected` или `UndefinedTableError`.
- **Restore rule:** если ради verify временно менялись `tests/.env.test`, port forward или другой PostgreSQL test endpoint, агент обязан вернуть canonical project state сразу после прогона и явно сообщить об этом в итоговой верификации.
- **Mocks and monkeypatching:** для unit-сценариев, которые не требуют реальной БД, canonical pattern — `monkeypatch`, `AsyncMock`, `MagicMock`, `SimpleNamespace`, как в [tests/test_database_unit.py](/home/lynx/telegram_shop_bot/tests/test_database_unit.py). Мокать нужно I/O boundary, а не внутренние assertions tested function.
- **Where to add tests:**
  - handler tests — в `tests/handlers/`
  - service/model/database tests — в существующие тематические файлы `tests/test_*.py`
  - новый файл допустим, если появляется новая устойчивая test surface, а не разовый кейс
- **Coverage expectations by change type:**
  - изменения в `app/services/` обычно требуют integration tests с `db_session`
  - изменения в `app/handlers/`, `app/keyboards/`, `app/callbacks/` требуют handler-level tests и при необходимости unit tests на text/rendering helpers
  - изменения в `app/models/`, `app/models/database.py` или миграциях требуют integration coverage на schema/constraint/CRUD regression
  - изменения в `app/config.py` и entrypoints требуют unit tests на конфигурацию и bootstrap behavior
- **CI reality:** текущий GitHub Actions workflow в [ci.yml](/home/lynx/telegram_shop_bot/.github/workflows/ci.yml) проверяет shell/tooling/markdown bootstrap, но не гоняет Python test suite. Поэтому для closure feature локальный прогон app-level тестов обязателен; отсутствие Python tests в CI нельзя трактовать как waiver.
- **Manual-only exceptions in this repo:** допустимы только для сценариев, где нужен live Telegram API, реальная доставка media по `image_url`, ручная проверка polling against bot token или внешняя платежная/CRM интеграция, которой в тестовом окружении нет. Такие gaps нужно явно перечислять в feature-плане с процедурой ручной проверки.
- **Pre-handoff minimum:** если изменение затрагивает только pure Python logic без БД, достаточно зелёного `-m unit`. Если изменение затрагивает SQLAlchemy, middleware с сессией, handlers каталога/корзины или миграции, нужен прогон `--run-integration` с доступной PostgreSQL.
