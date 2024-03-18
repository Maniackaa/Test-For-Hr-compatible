import asyncio
import datetime

from aiogram import Bot, Dispatcher

from config_data.bot_conf import conf, get_my_loggers

from handlers import echo, new_user, pay_handlers

logger, err_log = get_my_loggers()


async def main():
    logger.info('Starting bot')
    bot: Bot = Bot(token=conf.tg_bot.token, parse_mode='HTML')
    dp: Dispatcher = Dispatcher()

    # Регистрируем
    # dp.include_router(admin_handlers.router)
    dp.include_router(new_user.router)
    dp.include_router(pay_handlers.router)
    # dp.include_router(chat_handlers.router)

    # dp.include_router(user_handlers.router)
    dp.include_router(echo.router)

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        if conf.tg_bot.admin_ids:
            await bot.send_message(
                conf.tg_bot.admin_ids[0], f'Бот запущен.\n{datetime.datetime.now()}')
    except Exception:
        err_log.error(f'Не могу отравить сообщение {conf.tg_bot.admin_ids[0]}')
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Bot stopped!')