# Telegram Shop Bot

[![CI](https://github.com/lynxlg/telegram_shop_bot/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/lynxlg/telegram_shop_bot/actions/workflows/ci.yml)

Бот поддерживает базовый сценарий просмотра read-only каталога товаров: пользователь может открыть разделы, перейти по иерархии категорий и посмотреть карточку товара. Карточка товара поддерживает одно изображение по полю `image_url`.

## Запуск бота

```bash
.venv/bin/python -m app.main
```

## Запуск тестов

```bash
.venv/bin/pytest tests/ -v -m unit
```

## PostgreSQL в Docker для тестов

```bash
docker-compose up -d postgres
```

Полный прогон тестов с PostgreSQL:

```bash
.venv/bin/pytest tests/ -v --run-integration
```

Контейнерная PostgreSQL для тестов публикуется на `localhost:55432`.
