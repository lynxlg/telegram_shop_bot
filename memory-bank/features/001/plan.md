# Исправленный план реализации: Каталог товаров в Telegram-боте

## Замечания к plan-draft2

### 1. Шаг 1 всё ещё содержит неконкретную формулировку `при необходимости`

- Затронутый шаг: `1. Подготовить структуру пакетов для новой функциональности`
- Почему это проблема: критерий требует однозначных действий. Формулировка `при необходимости добавить __init__.py` оставляет решение исполнителю и делает шаг не полностью конкретным.
- Как исправить: зафиксировать одно решение. Для текущего проекта достаточно создать директории `app/services`, `app/callbacks`, `app/keyboards` без `__init__.py`, потому что проект уже работает как namespace package.

### 2. Пропущена явная проверка миграции через Alembic

- Затронутые шаги: `4. Создать миграцию каталога` и `17. Финальная проверка`
- Почему это проблема: план описывает создание миграции, но финальная проверка сводится только к `pytest` и ручному сценарию. Это не гарантирует, что Alembic-миграция действительно применима отдельно от `Base.metadata.create_all`.
- Как исправить: в финальную проверку добавить прогон миграции Alembic на тестовой или локальной БД и проверку, что схема поднимается без опоры на `create_all`.

## Исправленный порядок реализации

### 1. Подготовить структуру пакетов для новой функциональности

- Создать директории:
  - `app/services`
  - `app/callbacks`
  - `app/keyboards`
- Не добавлять `__init__.py`: текущий проект уже использует namespace package.

### 2. Добавить ORM-модели каталога

- Создать файл `app/models/category.py` с моделью `Category`:
  - `id: BigInteger`
  - `name: String(255)`
  - `parent_id: Optional[int]`
  - self-reference на родительскую категорию
- Создать файл `app/models/product.py` с моделью `Product`:
  - `id: BigInteger`
  - `category_id: BigInteger`
  - `name: String(255)`
  - `price: Numeric(10, 2)`
  - `description: Optional[str]`
  - `is_active: bool`
- Создать файл `app/models/product_attribute.py` с моделью `ProductAttribute`:
  - `id: BigInteger`
  - `product_id: BigInteger`
  - `name: String(100)`
  - `value: String(255)`

### 3. Подключить новые модели к metadata приложения и Alembic

- Обновить [app/models/database.py](/home/lynx/telegram_shop_bot/app/models/database.py):
  - в `init_db()` импортировать `app.models.category`, `app.models.product`, `app.models.product_attribute` рядом с `app.models.user`
- Обновить [alembic/env.py](/home/lynx/telegram_shop_bot/alembic/env.py):
  - добавить импорты `Category`, `Product`, `ProductAttribute`, чтобы `target_metadata` содержала все таблицы

### 4. Создать миграцию каталога

- Создать новую миграцию в `alembic/versions/`:
  - таблица `categories`
  - таблица `products`
  - таблица `product_attributes`
  - внешние ключи
  - индексы по `parent_id`, `category_id`, `product_id`, `is_active`
  - тип `Numeric(10, 2)` для `products.price`
- Проверить, что имена таблиц и типы совпадают с ORM-моделями из шага 2.

### 5. Реализовать read-only query layer каталога

- Создать файл `app/services/catalog.py`.
- Добавить async-функции:
  - `get_root_categories(session: AsyncSession) -> List[Category]`
  - `get_category_by_id(session: AsyncSession, category_id: int) -> Optional[Category]`
  - `get_child_categories(session: AsyncSession, category_id: int) -> List[Category]`
  - `get_active_products_by_category(session: AsyncSession, category_id: int) -> List[Product]`
  - `get_product_by_id(session: AsyncSession, product_id: int) -> Optional[Product]`
  - `get_product_attributes(session: AsyncSession, product_id: int) -> List[ProductAttribute]`
- Зафиксировать сортировку:
  - категории по `name`
  - товары по `name`
- Зафиксировать правило выборки:
  - в списках товаров показывать только `is_active = True`

### 6. Реализовать текстовые formatter-функции

- Создать файл `app/services/catalog_text.py`.
- Добавить функции:
  - `build_categories_text(categories)`
  - `build_products_text(category, products)`
  - `build_product_text(product, attributes)`
- Зафиксировать fallback:
  - пустое описание: `Описание отсутствует.`
  - пустые характеристики: `Характеристики не указаны.`
- Зафиксировать единый формат цены для `Numeric(10, 2)`, используемый во всех handler'ах.

### 7. Реализовать callback schema каталога

- Создать файл `app/callbacks/catalog.py`.
- Добавить типизированный `CallbackData` с фиксированными полями:
  - `action: str`
  - `category_id: Optional[int]`
  - `product_id: Optional[int]`
  - `parent_category_id: Optional[int]`
- Использовать значения `action`:
  - `open_category`
  - `open_product`
  - `go_back`

### 8. Реализовать inline-клавиатуры каталога

- Создать файл `app/keyboards/catalog.py`.
- Добавить builder-функции:
  - клавиатура корневых категорий
  - клавиатура дочерних категорий
  - клавиатура списка товаров листовой категории
  - клавиатура карточки товара с кнопкой `Назад`
- Использовать `InlineKeyboardBuilder` и callback-схему из `app/callbacks/catalog.py`.

### 9. Реализовать главное меню

- Создать файл `app/keyboards/main_menu.py`.
- Добавить функцию `get_main_menu_keyboard()` с reply-клавиатурой и кнопкой `Каталог`.
- Обновить [app/handlers/common/start.py](/home/lynx/telegram_shop_bot/app/handlers/common/start.py):
  - в успешном ответе на `/start` отдавать клавиатуру главного меню
  - не менять текущую логику регистрации пользователя

### 10. Реализовать router каталога

- Создать файл `app/handlers/catalog.py`.
- Добавить `Router` и обработчики:
  - вход по тексту `Каталог`
  - callback `open_category`
  - callback `open_product`
  - callback `go_back`
- В handler'ах использовать:
  - `app/services/catalog.py` для чтения данных
  - `app/services/catalog_text.py` для текста
  - `app/keyboards/catalog.py` для клавиатур
- В каждом handler'е обернуть обращения к БД в `try/except SQLAlchemyError` с `logger.exception(...)` и пользовательским сообщением `Не удалось загрузить каталог. Попробуйте позже.`
- Явно покрыть ветки:
  - каталог пуст
  - категория не найдена
  - товар не найден
  - листовая категория без товаров

### 11. Подключить новый router в приложение

- Обновить [app/main.py](/home/lynx/telegram_shop_bot/app/main.py):
  - импортировать router из `app.handlers.catalog`
  - подключить его через `dispatcher.include_router(...)`
- Не менять порядок инициализации БД и middleware.

### 12. Обновить тестовую инфраструктуру под новые таблицы и router'ы

- Обновить [tests/conftest.py](/home/lynx/telegram_shop_bot/tests/conftest.py):
  - импортировать новые модели, чтобы `Base.metadata.create_all` создавала таблицы каталога
  - добавить фабрики данных для категорий, товаров и атрибутов
  - расширить cleanup после тестов: `TRUNCATE` таблиц `product_attributes`, `products`, `categories`, `users`
  - обновить `dp`-фикстуру так, чтобы она подключала `start_router` и `catalog_router`

### 13. Добавить тесты query layer

- Создать файл `tests/test_catalog_service.py`.
- Добавить независимые тесты на:
  - корневые категории
  - дочерние категории
  - отсутствие дочерних категорий у листовой категории
  - фильтрацию только активных товаров
  - загрузку товара
  - загрузку атрибутов

### 14. Добавить тесты handler'ов каталога

- Создать файл `tests/handlers/test_catalog.py`.
- Добавить тесты на сценарии:
  - вход в каталог показывает корневые категории
  - пустой каталог
  - переход в дочернюю категорию
  - переход в листовую категорию
  - листовая категория без товаров
  - открытие карточки товара
  - fallback для описания
  - fallback для характеристик
  - `Назад` возвращает на один экран выше
  - несуществующая категория
  - несуществующий товар
  - ошибка БД

### 15. Обновить существующие тесты на wiring приложения

- Обновить [tests/test_main.py](/home/lynx/telegram_shop_bot/tests/test_main.py):
  - адаптировать проверку `include_router` под подключение router `start` и router `catalog`
- Обновить [tests/handlers/test_start.py](/home/lynx/telegram_shop_bot/tests/handlers/test_start.py):
  - проверить, что `/start` возвращает reply-клавиатуру с кнопкой `Каталог`

### 16. Обновить пользовательскую документацию

- Обновить [README.md](/home/lynx/telegram_shop_bot/README.md):
  - кратко описать, что бот поддерживает read-only каталог
  - оставить актуальные команды запуска и тестов

### 17. Финальная проверка

- Прогнать `pytest`
- Применить Alembic-миграции на тестовой или локальной БД и убедиться, что схема поднимается без `Base.metadata.create_all`
- Проверить вручную сценарии:
  - `Каталог` с корневыми категориями
  - переход в дочерние категории
  - листовая категория с товарами
  - карточка товара
  - `Назад`
  - пустой каталог
  - ошибка загрузки каталога

## Критерий готовности

Фича считается готовой, когда:

- пользователь получает reply-клавиатуру с кнопкой `Каталог` после `/start`;
- может открыть корневые категории;
- может пройти в дочерние категории;
- может открыть список активных товаров листовой категории;
- может открыть карточку товара;
- получает fallback для `description` и `attributes`;
- кнопка `Назад` работает на один экран вверх;
- Alembic-миграция и ORM-схема согласованы;
- тесты на query layer, handler'ы и wiring проходят.
