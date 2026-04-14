---
title: Coding Style
doc_kind: engineering
doc_function: convention
purpose: Project-specific coding style для Python/Aiogram/SQLAlchemy репозитория, включая правила локальной сложности и engineering tooling baseline.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
---

# Coding Style

## General Rules

- Основной язык проекта — Python 3 с async/await, Aiogram 3 и SQLAlchemy 2.x. Новый код должен продолжать этот стек, а не вводить альтернативные frameworks без отдельного решения.
- Имена переменных, функций, модулей и файлов — `snake_case`; классы ORM, middleware и callback data classes — `PascalCase`; константы пользовательских сообщений и action IDs — `UPPER_SNAKE_CASE`.
- Комментарии добавляются только там, где без них трудно понять мотив, инвариант или boundary condition. Очевидные строки не комментируются.
- Предпочитай минимальную локальную сложность: если поведение помещается в один handler/service без общего reusable abstraction, не выноси его преждевременно в новый слой.

## Tooling Contract

- Отдельный formatter/linter для Python в репозитории пока не зафиксирован. Canonical baseline — PEP 8-совместимый стиль, читаемые импорты, типы там, где они уже используются, и прохождение существующих тестов.
- Для shell-скриптов canonical tooling уже есть в CI: `shfmt` и `shellcheck`. Любое изменение в `init.sh` или `scripts/*.sh` должно оставаться совместимым с этими проверками.
- Если в репозитории позже появятся `ruff`, `black` или pre-commit hooks, этот документ должен стать canonical owner новых правил вместо локальных договорённостей "по привычке".

## Python Backend

- Границы модулей:
  - `app/handlers/` принимает Telegram events и координирует flow
  - `app/services/` содержит query/business logic и text builders
  - `app/models/` владеет ORM schema и database bootstrap
  - `app/keyboards/` и `app/callbacks/` владеют Telegram UI contracts
- Handlers должны оставаться тонкими: извлекать входные данные, вызывать services, рендерить ответ и логировать ошибку. Запросы к БД, сортировка и rule-heavy логика должны жить в `services/` или вспомогательных функциях, а не расползаться по handler branches.
- Для I/O-путей используй `async`/`await`; не добавляй синхронные блокирующие вызовы в runtime flow.
- Для зависимостей БД используется `AsyncSession`, передаваемая явно параметром `db`/`session`. Не создавай ad hoc engine/session внутри handlers или services.
- Ошибки инфраструктуры ловятся на границе I/O и логируются через `logger.exception(...)` с контекстом идентификаторов (`telegram_id`, `product_id`, `cart_item_id`), как уже сделано в handlers и services.
- Там, где возможна осмысленная доменная, инфраструктурная или внешняя I/O-ошибка, оборачивай boundary в `try`/`except` и логируй исключение с полезным контекстом.
- Для nullable-результатов используй `Optional[...]` и явную ветку `None`, а не неявные truthy/falsy договорённости.
- Для типизации придерживайся стандартных generic-типов проекта: `List`, `Dict`, `Optional`, `Union`, если файл уже следует этой конвенции или изменение продолжает существующий локальный стиль.
- Денежные значения в доменной модели должны оставаться `Decimal`-совместимыми (`Numeric(10, 2)` в модели `Product`). Не переводи цены в `float`.

## Grounding And Contracts

- Не придумывай API, env-контракты, callback payloads, schema shape или внешние интеграционные соглашения без проверки по коду, тестам, миграциям или canonical documentation в `memory-bank/`.
- Если для изменения нужна документация по сторонней библиотеке или внешнему API, сначала используй authoritative docs/tooling; в агентской среде canonical путь для этого — `context7`, если документация доступна через него.
- Локальные project-specific факты при этом подтверждаются кодом, тестами, миграциями и governed-документами репозитория, а не внешними примерами "по аналогии".

## Aiogram Conventions

- Роутеры объявляются модульно и подключаются в bootstrap-слое через `include_router`, как в [app/main.py](/home/lynx/telegram_shop_bot/app/main.py).
- Callback data и action constants считаются частью Telegram contract. При изменении action names, состава payload или keyboard navigation нужны сопутствующие tests.
- Пользовательские тексты, которые используются в нескольких ветках одного сценария, лучше держать в именованных константах или text helper modules, а не дублировать строковые литералы по всему handler.

## SQLAlchemy And Migrations

- ORM модели используют typed declarative mapping (`Mapped[...]`, `mapped_column`). Новый ORM-код должен продолжать этот стиль.
- Все schema changes оформляются через Alembic migration в `alembic/versions/`; править только модели без миграции допустимо лишь когда изменение не затрагивает реальную схему.
- Для foreign keys и каскадов следуй уже существующим patterns (`ondelete="CASCADE"`, relationship `cascade="all, delete-orphan"`), если нет явной причины их менять.
- Bootstrap БД и вспомогательные функции вроде `ensure_database_exists()` остаются в `app/models/database.py`; не дублируй похожую логику по entrypoints.

## Test Code

- Для unit tests предпочитай `monkeypatch` и `AsyncMock` на I/O boundary.
- Для integration tests предпочитай реальные ORM-объекты и session commits/flushes вместо глубокого мокинга SQLAlchemy.
- Новые fixtures добавляй в `tests/conftest.py`, только если они реально переиспользуются в нескольких test modules.

## Change Discipline

- Не переписывай несвязанные модули только ради единообразия.
- При touch-up изменениях следуй существующему локальному стилю файла, если он не конфликтует с правилами выше.
- Если в кодовой базе уже есть два конкурирующих паттерна, не выбирай молча третий. Либо используй доминирующий локальный pattern, либо подними вопрос как архитектурный trade-off.
