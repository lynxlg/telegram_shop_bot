# Telegram Shop Bot

[![CI](https://github.com/lynxlg/telegram_shop_bot/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/lynxlg/telegram_shop_bot/actions/workflows/ci.yml)

Бот поддерживает каталог, корзину, checkout заказов, operator workflow по заказам и online-оплату через YooKassa. После оформления заказа пользователь может получить ссылку на оплату, а webhook `payment.succeeded` переводит заказ в `paid`.

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
