import asyncio
import logging

from app.bot import create_bot, create_dispatcher
from app.handlers.admin_catalog import router as admin_catalog_router
from app.handlers.cart import router as cart_router
from app.handlers.catalog import router as catalog_router
from app.handlers.common.start import router as start_router
from app.handlers.operator_orders import router as operator_orders_router
from app.handlers.order_status import router as order_status_router
from app.middlewares.db_session import DbSessionMiddleware
from app.models.database import dispose_engine, init_db

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    bot = create_bot()
    dispatcher = create_dispatcher()

    dispatcher.update.middleware(DbSessionMiddleware())
    dispatcher.include_router(start_router)
    dispatcher.include_router(catalog_router)
    dispatcher.include_router(cart_router)
    dispatcher.include_router(order_status_router)
    dispatcher.include_router(operator_orders_router)
    dispatcher.include_router(admin_catalog_router)

    try:
        await init_db()
        logger.info("Bot is starting")
        await dispatcher.start_polling(bot)
    except Exception:
        logger.exception("Bot stopped due to an unexpected error")
        raise
    finally:
        await bot.session.close()
        await dispose_engine()
        logger.info("Bot shutdown completed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
