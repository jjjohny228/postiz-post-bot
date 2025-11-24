from aiogram import executor

from src.handlers import register_user_handlers
from src.create_bot import dp, bot
from src.utils import logger


async def on_startup(_):
    # Handler registration
    register_user_handlers(dp)

    logger.info('The bot is up and running!')


async def on_shutdown(_):
    await (await bot.get_session()).close()


def start_bot():
    try:
        executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)
    except Exception as e:
        logger.error(e)
