from __future__ import annotations

import logging

from aiogram import Bot
from aiohttp import web
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import get_settings
from app.keyboards.payment import build_retry_payment_keyboard
from app.models.database import async_session_factory
from app.services.payment import (
    is_yookassa_enabled,
    process_yookassa_notification,
)

logger = logging.getLogger(__name__)
settings = get_settings()


async def handle_yookassa_webhook(request: web.Request) -> web.Response:
    bot: Bot = request.app["bot"]
    session_factory: async_sessionmaker = request.app["session_factory"]
    payload = await request.json()

    async with session_factory() as session:
        result = await process_yookassa_notification(session, payload)

    if (
        result.should_notify_buyer
        and result.order is not None
        and result.order.user is not None
        and result.buyer_text is not None
    ):
        reply_markup = None
        if result.attempt is not None and result.attempt.status == "canceled":
            reply_markup = build_retry_payment_keyboard(result.order.id)
        await bot.send_message(
            result.order.user.telegram_id,
            result.buyer_text,
            reply_markup=reply_markup,
        )

    return web.json_response({"ok": True})


async def start_yookassa_webhook_server(bot: Bot) -> web.AppRunner | None:
    if not is_yookassa_enabled():
        return None

    app = web.Application()
    app["bot"] = bot
    app["session_factory"] = async_session_factory
    app.router.add_post(settings.yookassa_webhook_path, handle_yookassa_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
        runner, host=settings.yookassa_webhook_host, port=settings.yookassa_webhook_port
    )
    await site.start()
    logger.info(
        "YooKassa webhook server started host=%s port=%s path=%s",
        settings.yookassa_webhook_host,
        settings.yookassa_webhook_port,
        settings.yookassa_webhook_path,
    )
    return runner


async def stop_yookassa_webhook_server(runner: web.AppRunner | None) -> None:
    if runner is not None:
        await runner.cleanup()
