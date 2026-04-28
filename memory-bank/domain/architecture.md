---
title: Architecture Patterns
doc_kind: domain
doc_function: canonical
purpose: Каноничное место для архитектурных границ проекта. Читать при изменениях, затрагивающих модули, фоновые процессы, интеграции или конфигурацию.
derived_from:
  - ../dna/governance.md
status: active
audience: humans_and_agents
---

# Architecture Patterns

Этот документ фиксирует текущие архитектурные правила проекта, а не абстрактный шаблон. Он описывает реальные границы слоёв в `app/`, способы работы с PostgreSQL и ограничения aiogram runtime.

## Module Boundaries

| Context | Owns | Must not depend on directly |
| --- | --- | --- |
| `handlers` | aiogram routers, mapping Telegram events to use cases, user-facing error messages | raw SQL, keyboard internals, direct env parsing |
| `services` | query/use-case logic for catalog and cart, orchestration of model reads and writes | aiogram message objects, reply text formatting details |
| `models` | SQLAlchemy models, session factory, engine lifecycle, schema bootstrap | Telegram event handling |
| `keyboards` and `callbacks` | Telegram UI navigation contracts: reply keyboard, inline buttons, callback payload schema | database access and business persistence |
| `config` | loading runtime settings from env via `pydantic-settings` | handler/service decisions |

Правила по слоям:

- `handlers` вызывают `services` и `keyboards`, но не должны встраивать SQL-запросы или владеть persistence-логикой.
- `services` работают через `AsyncSession` и модели SQLAlchemy, но не должны принимать aiogram-объекты как аргументы.
- `keyboards` и `services/*_text.py` владеют presentation-level Telegram formatting; остальной код не должен дублировать callback schema или текстовую раскладку экранов.
- Новые продуктовые области добавляются как отдельные handlers/services/models slices, а не как расширение уже существующих файлов произвольной логикой.

## Concurrency And Critical Sections

Проект сейчас не использует job queue, внешние фоновые воркеры или отдельный lock manager. Основная конкурентность проходит через независимую обработку Telegram updates и отдельный `AsyncSession` на событие через `DbSessionMiddleware`.

Разрешённый pattern:

- одна пользовательская операция обрабатывается в рамках одного handler вызова и одного `AsyncSession`;
- `services/cart.py` выполняет чтение, изменение и `commit` в одном сервисном вызове;
- при ошибке записи используется `rollback`, после чего handler показывает domain-safe сообщение без технических деталей.

Ограничения текущего baseline:

- в проекте нет явного row-level locking, optimistic locking или идемпотентных ключей для корзины;
- поэтому новые сценарии, где два update могут конфликтовать за один и тот же бизнес-объект, нельзя молча реализовывать по аналогии с текущим MVP;
- если feature добавляет checkout, оплату, резервирование остатков или другой truly critical write path, нужен отдельный ADR или как минимум явное архитектурное решение по concurrency.

Границы транзакции сейчас проходят внутри сервисов БД и не должны пересекаться с внешними API: сначала обновление локального состояния, потом внешний side effect. Для текущего scope это означает, что каталог и корзина не должны комбинировать DB transaction с вызовами сторонних сервисов внутри одного "best effort" блока.

## Failure Handling And Error Tracking

Единый подход в текущем коде такой:

- `services` логируют и пробрасывают `SQLAlchemyError` вверх после `rollback`, если сервис меняет состояние.
- `handlers` переводят инфраструктурную ошибку в пользовательский verdict: `Не удалось загрузить каталог. Попробуйте позже.`, `Не удалось обновить корзину. Попробуйте позже.` и т.п.
- доменные состояния "не найдено" или "пусто" не считаются исключениями и возвращаются как обычный результат (`None`, пустой список).
- логирование ведётся через стандартный `logging`; contextual metadata добавляется в сообщение лога через идентификаторы вроде `telegram_id`, `category_id`, `product_id`, `cart_item_id`.

Что запрещено:

- показывать пользователю traceback или сырой текст исключения;
- дублировать `try/except` с глушением ошибки без лога;
- смешивать domain verdict и инфраструктурную аварию в одно и то же значение без понятного пользовательского ответа.

Retry policy в проекте пока не вынесена в инфраструктуру. Если появятся внешние интеграции или фоновые джобы, правила retry нужно будет зафиксировать отдельно, а не предполагать их наличие по умолчанию.

## Configuration Ownership

Canonical schema runtime-конфигурации живёт в [app/config.py](../../app/config.py) в классе `Settings`.

Ownership-модель:

1. `app.config.Settings` владеет перечнем поддерживаемых env-переменных, типами, значениями по умолчанию и способом загрузки из `.env`.
2. Код приложения получает настройки только через `get_settings()` и не должен вручную читать `os.environ` в handlers/services.
3. `app.models.database` владеет производным использованием `database_url`: engine, session factory, bootstrap БД.
4. Документация по запуску и окружению должна синхронизироваться с `README.md`, `SETUP.md` и далее с `memory-bank/ops/config.md`, когда секция `ops` будет адаптирована под этот репозиторий.

Текущий минимальный env contract:

- `bot_token` — токен Telegram-бота;
- `database_url` — DSN для `postgresql+asyncpg`.

Если добавляется новая настройка:

1. сначала обновить `app/config.py`;
2. затем обновить код-owners этой настройки;
3. затем синхронизировать runtime documentation.
