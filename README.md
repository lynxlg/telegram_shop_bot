# Telegram Shop Bot

[![CI](https://github.com/lynxlg/telegram_shop_bot/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/lynxlg/telegram_shop_bot/actions/workflows/ci.yml)

Бот поддерживает базовый сценарий просмотра каталога и работы с корзиной: пользователь может открыть разделы, перейти по иерархии категорий, посмотреть карточку товара, добавить товар в корзину и затем управлять количеством позиций. Карточка товара поддерживает одно изображение по полю `image_url`, а корзина сохраняется в PostgreSQL между сессиями.

## Запуск бота

```bash
.venv/bin/python -m app.main
```

## Запуск тестов

```bash
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/pytest tests/ -v -m unit
```

## PostgreSQL в Docker для тестов

```bash
docker-compose up -d postgres
```

Полный прогон тестов с PostgreSQL:

```bash
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/pytest tests/ -v --run-integration
```

Полный локальный verify с lint перед тестами:

```bash
./scripts/run-tests.sh
```

Установить git hooks для автоматического запуска перед коммитом:

```bash
.venv/bin/pre-commit install
```

Контейнерная PostgreSQL для тестов публикуется на `localhost:55432`.
