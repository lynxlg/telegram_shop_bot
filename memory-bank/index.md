---
title: Project Documentation Index
doc_kind: project
doc_function: index
purpose: Корневая навигация по project-specific memory-bank. Читать сначала, чтобы понять структуру authoritative документации этого репозитория.
derived_from:
  - dna/principles.md
  - dna/governance.md
status: active
audience: humans_and_agents
---

# Documentation Index

Каталог `memory-bank/` содержит authoritative документацию репозитория `telegram_shop_bot`: governance-правила, domain context, engineering conventions, operational ограничения и feature packages.

Шаблонные wrapper-документы остаются только в `flows/templates/`; остальная active-документация должна описывать этот проект, а не абстрактный template.

## Кратко о проекте

`telegram_shop_bot` — Telegram-бот интернет-магазина. Текущий product baseline покрывает `/start` с role-aware главным меню, навигацию по иерархическому каталогу, карточку товара с изображением по `image_url`, корзину в PostgreSQL, checkout с созданием заказа, buyer-facing просмотр активных заказов, operator workflow смены статусов, buyer notifications и admin CRUD каталога.

## Стек

- `Python`
- `Aiogram`
- `SQLAlchemy async`
- `PostgreSQL`
- `pydantic-settings`

## Архитектура

Проект организован по слоям `handlers` → `services` → `models`, с отдельными пакетами `keyboards`/`callbacks` для Telegram UI, `ui_text.py` + `ui_texts.json` для централизованного copy и `config` для загрузки runtime-настроек. `handlers` принимают Telegram updates и вызывают use case-логику, `services` работают с `AsyncSession` и бизнес-операциями каталога, корзины и заказов, `models` владеют SQLAlchemy-моделями и lifecycle БД.

## Аннотированный индекс

- [`domain/README.md`](domain/README.md)
  **Что:** Индекс domain-документации проекта: общий product context, архитектурные границы и правила Telegram UI. Отсюда агент переходит к problem statement, architecture patterns и frontend conventions.
  **Читать, чтобы:** понять бизнес-контекст системы перед изменениями в продукте, слоях приложения или пользовательских сценариях.

- [`prd/README.md`](prd/README.md)
  **Что:** Индекс PRD-документов для продуктовых инициатив, которые стоят между общим контекстом проекта и конкретными feature packages. Объясняет, когда PRD нужен, а когда достаточно `domain/problem.md` или одной feature.
  **Читать, чтобы:** завести или найти initiative-level требования, если задача распадается на несколько фич и требует отдельного product scope.

- [`use-cases/README.md`](use-cases/README.md)
  **Что:** Индекс канонических `UC-*` сценариев проекта с правилами, когда use case считается отдельной сущностью, а когда сценарий должен остаться внутри feature. Фиксирует назначение use-case слоя и naming rules.
  **Читать, чтобы:** зарегистрировать устойчивый пользовательский или операционный flow либо проверить, нужен ли для задачи отдельный use case.

- [`ops/README.md`](ops/README.md)
  **Что:** Индекс operational-документации репозитория: локальная разработка, конфигурация, окружения, релизы и runbooks. Служит точкой входа в runtime и deployment context проекта, включая runbook по integration tests через Docker PostgreSQL.
  **Читать, чтобы:** подготовить окружение, проверить config expectations, понять ограничения non-local сред или найти operational runbook по локальному PostgreSQL и verify.

- [`engineering/README.md`](engineering/README.md)
  **Что:** Индекс engineering-правил репозитория: testing policy, coding style, git workflow и autonomy boundaries. Также фиксирует рабочий язык project-specific документации и агентского взаимодействия.
  **Читать, чтобы:** понять, как здесь писать код, чем его проверять и где агент обязан остановиться перед рискованными действиями.

- [`dna/README.md`](dna/README.md)
  **Что:** Точка входа в governance-слой memory-bank: принципы SSoT, dependency tree, frontmatter schema, lifecycle и cross-references. Это конституция документации проекта.
  **Читать, чтобы:** проверить правила authoritative документации, определить owner факта или валидно обновить governed-документы.

- [`flows/README.md`](flows/README.md)
  **Что:** Индекс process-layer документации: task workflows, lifecycle feature package и governed templates. Объясняет, как создавать новые документы и вести фичу по этапам delivery.
  **Читать, чтобы:** выбрать правильный flow для задачи, создать feature package по правилам или инстанцировать новый документ из шаблона.

- [`adr/README.md`](adr/README.md)
  **Что:** Индекс instantiated ADR проекта с правилами именования, статусами решений и ссылкой на шаблон. Определяет, как хранить принятые архитектурные решения в репозитории.
  **Читать, чтобы:** найти существующее архитектурное решение или оформить новое решение в виде ADR.

- [`features/README.md`](features/README.md)
  **Что:** Индекс feature packages вида `FT-XXX/` с правилами naming, связью с feature flow и границей между canonical packages и legacy-архивом. Фиксирует, где живут delivery-единицы проекта.
  **Читать, чтобы:** найти существующую фичу, создать новую delivery-единицу или проверить, считается ли пакет canonical в текущем процессе.
