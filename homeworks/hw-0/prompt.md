Первый промпт

## Задача
Реализовать базовый функционал Telegram-бота: подключение к Telegram Bot API, команду `/start`, регистрацию нового пользователя и сохранение его данных в PostgreSQL.

## Контекст
- **Смотри файлы** (создай их, если отсутствуют):
  - `app/config.py` — настройки с переменными окружения (BOT_TOKEN, DATABASE_URL)
  - `app/models/database.py` — инициализация async SQLAlchemy
  - `app/models/user.py` — ORM модель User
  - `app/bot.py` — создание экземпляра Bot и Dispatcher
  - `app/main.py` — точка входа с запуском polling
  - `app/handlers/common/start.py` — обработчик команды /start
  - `app/middlewares/db_session.py` — middleware для внедрения сессии БД
  - `.env` — файл с переменными окружения

- **Технологии**:
  - Python 3.11+
  - aiogram 3.x
  - SQLAlchemy 2.0 (async)
  - asyncpg
  - pydantic-settings

- **Ограничения**:
  - НЕ использовать синхронные драйверы БД (только asyncpg)
  - НЕ блокировать event loop (все I/O операции — async/await)
  - НЕ хранить секреты в коде (только через переменные окружения)
  - НЕ использовать FSM для этой задачи (простая команда)
  - НЕ создавать лишних файлов, только указанные выше

## Шаги
1. **Настройка конфигурации**: создать `config.py` с классом `Settings`, загружающим BOT_TOKEN, DATABASE_URL из `.env`
2. **Модель пользователя**: определить `User` с полями: id (BigInteger, PK), telegram_id (BigInteger, unique), username, first_name, last_name, phone (nullable), role (default='user'), created_at, last_activity
3. **Database setup**: создать `database.py` с async engine, session factory, Base, и функцией `get_db()`
4. **Миграция/инициализация**: при старте бота вызвать `init_db()` для создания таблиц (в production использовать Alembic)
5. **Middleware для БД**: добавить middleware, который для каждого апдейта создает сессию и кладет в `data['db']`
6. **Обработчик /start**: 
   - Получить данные пользователя из Telegram (message.from_user)
   - Проверить, существует ли пользователь в БД по `telegram_id`
   - Если нет — создать нового, заполнив telegram_id, username, first_name, last_name
   - Обновить поле `last_activity` при любом обращении
   - Отправить приветственное сообщение
7. **Главный файл**: в `main.py` объединить всё: создание бота, диспетчера, регистрацию middleware и хендлера, запуск polling

## Критерии готовности
- [ ] Бот отвечает на команду `/start` приветственным сообщением
- [ ] При первом запуске пользователь добавляется в таблицу `users` в PostgreSQL
- [ ] При повторном `/start` не создается дубликат, только обновляется `last_activity`
- [ ] В консоли/log-файле отображаются сообщения о старте бота и регистрации пользователя
- [ ] Код обрабатывает ошибки подключения к БД и логирует их
- [ ] Все секреты загружаются из `.env` (пример `.env.example` прилагается)
- [ ] Бот корректно завершает работу по Ctrl+C (graceful shutdown)

## Пример (ожидаемая структура)

**app/config.py:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    bot_token: str
    database_url: str
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**app/models/user.py:**
```python
from sqlalchemy import Column, BigInteger, String, DateTime, func
from app.models.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    phone = Column(String(20))
    role = Column(String(20), default="user")
    created_at = Column(DateTime, server_default=func.now())
    last_activity = Column(DateTime, onupdate=func.now())
```

**app/handlers/common/start.py:**
```python
from aiogram import Router, types
from aiogram.filters import Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, session: AsyncSession):
    # логика регистрации
    ...
    await message.answer("Добро пожаловать!")
```

**app/main.py:**
```python
async def main():
    # инициализация БД
    await init_db()
    # запуск бота
    ...
```

Второй промпт

## Задача
Написать интеграционные и модульные тесты для базового функционала Telegram-бота: подключение к БД, регистрация пользователя через `/start`, сохранение данных в PostgreSQL, обработка повторных обращений.

## Контекст
- **Смотри файлы**:
  - `app/config.py` — конфигурация с Settings
  - `app/models/database.py` — setup БД
  - `app/models/user.py` — ORM модель User
  - `app/handlers/common/start.py` — обработчик `/start`
  - `app/middlewares/db_session.py` — middleware для сессий
  - `app/main.py` — точка входа
  - `.env.test` — тестовые переменные окружения

- **Технологии**:
  - pytest 8.x
  - pytest-asyncio 0.23+
  - pytest-env 1.1+
  - pytest-mock 3.12+
  - sqlalchemy-utils (для создания тестовой БД)
  - asyncpg
  - aiogram 3.x (MemoryStorage для тестов)

- **Ограничения**:
  - НЕ использовать реальный Telegram API (мокать aiogram.types.Update/Message)
  - НЕ создавать реальные сетевые запросы
  - НЕ оставлять артефакты после тестов (чистить таблицы/БД)
  - НЕ использовать `asyncio.run()` в тестах (использовать `pytest.mark.asyncio`)
  - Тесты должны быть изолированными (каждый тест — чистое состояние)

## Шаги

### 1. Структура тестов
Создать следующую структуру:
```
tests/
├── __init__.py
├── conftest.py                 # Фикстуры (bot, dp, session, db_engine)
├── test_config.py              # Тесты конфигурации
├── test_database.py            # Тесты подключения и моделей
├── handlers/
│   ├── __init__.py
│   └── test_start.py           # Тесты /start хендлера
└── .env.test                   # Тестовые переменные
```

### 2. Фикстуры в conftest.py
- `test_settings` — загрузка конфигурации из `.env.test`
- `test_engine` — создание async engine для тестовой БД (создавать БД, если нет)
- `test_session_factory` — фабрика сессий
- `db_session` — отдельная сессия для каждого теста (с транзакцией и откатом)
- `bot` — мок Bot (или реальный с MemoryStorage)
- `dp` — Dispatcher с зарегистрированными хендлерами
- `message` — фабрика создания мок-сообщений от aiogram

### 3. Тесты конфигурации
- Проверить, что переменные окружения загружаются
- Проверить, что при отсутствии `.env` используются значения по умолчанию
- Проверить валидацию обязательных полей

### 4. Тесты БД
- Проверить, что подключение к БД успешно
- Проверить, что таблицы создаются
- Проверить, что модель User сохраняется и извлекается
- Проверить уникальность `telegram_id`

### 5. Тесты хендлера /start
- **Тест 1:** Новый пользователь — регистрация в БД, приветственное сообщение
- **Тест 2:** Существующий пользователь — обновление `last_activity`, НЕ создание дубликата
- **Тест 3:** Проверка сохранения всех полей (telegram_id, username, first_name, last_name)
- **Тест 4:** Проверка обновления `last_activity` при повторном обращении
- **Тест 5:** Обработка ошибок БД (падение при сохранении) — бот должен отвечать с ошибкой, но не крашиться

### 6. Тесты middleware
- Проверить, что `db` добавляется в `data`
- Проверить, что сессия закрывается после обработки
- Проверить, что при ошибке в хендлере сессия всё равно закрывается

## Критерии готовности
- [ ] Все тесты проходят успешно (`pytest tests/ -v`)
- [ ] Покрытие кода основных функций не менее 80%
- [ ] Тесты используют отдельную тестовую БД (не затрагивают разработческую)
- [ ] Тесты изолированы (порядок выполнения не важен)
- [ ] Тесты работают с мок-сообщениями, не отправляя реальные запросы в Telegram
- [ ] Добавлен `pytest.ini` с настройками (asyncio_mode = auto)
- [ ] Добавлен скрипт для запуска тестов с созданием тестовой БД


### .env.test
```bash
# Тестовая БД (создается автоматически)
DATABASE_URL=postgresql://postgres:password@localhost:5432/shop_bot_test

# Не используется, но нужен для валидации
BOT_TOKEN=test_token_12345

# Тестовые настройки
LOG_LEVEL=ERROR
```

### requirements-test.txt
```
pytest==8.3.4
pytest-asyncio==0.23.8
pytest-env==1.1.5
pytest-mock==3.14.0
pytest-cov==6.0.0
sqlalchemy-utils==0.41.2
asyncpg==0.30.0
httpx==0.27.2
```

## Дополнительные указания
- Тесты должны запускаться командой `pytest tests/ -v --cov=app --cov-report=term-missing`
- Использовать `pytest.mark.asyncio` для всех асинхронных тестов
- В CI/CD окружении тестовая БД должна создаваться отдельно (через docker-compose или GitHub Actions services)
- Мокировать `bot.send_message` и `message.answer` через `AsyncMock` (aiogram автоматически создает моки, но можно явно)
- Проверить, что middleware корректно передает `db_session` в хендлер