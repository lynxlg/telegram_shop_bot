# Telegram Shop Bot

[![CI](https://github.com/lynxlg/telegram_shop_bot/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/lynxlg/telegram_shop_bot/actions/workflows/ci.yml)

Бот поддерживает базовый сценарий просмотра read-only каталога товаров: пользователь может открыть разделы, перейти по иерархии категорий и посмотреть карточку товара.

## Запуск бота

```bash
.venv/bin/python -m app.main
```

## Запуск тестов

```bash
.venv/bin/pytest tests/ -v --cov=app --cov-report=term-missing
```
