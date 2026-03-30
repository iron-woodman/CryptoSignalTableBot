import asyncio
import logging
import threading

from aiohttp import web
from aiogram import Dispatcher, Router, types

from bot.config import CHAT_ID, EXCHANGE, WEBHOOK_PATH, WEBHOOK_PORT, WEBHOOK_URL
from services.telegram.bot import bot
from utils.tg_signal2 import parse_signal_data2
from utils.google_sheet import init_gspread_client, get_old_orders, get_empty_row, get_order_number
from utils.track_positions import track_position, row_order_iterator
from utils.logger_setup import logger
from workers.telegram_worker import worker

dp = Dispatcher()
router = Router()
worker_task: asyncio.Task | None = None
worksheet = None


@router.channel_post()
async def on_channel_post(message: types.Message) -> None:
    global worksheet

    if not message.text:
        return

    parsed_signal = parse_signal_data2(message.text)
    if parsed_signal:
        # Не отправляем начальное сообщение Signal: ... в канал
        # process_signal(parsed_signal, chat_id=CHAT_ID)

        if worksheet is not None:
            try:
                empty_row = get_empty_row(worksheet)
                if empty_row:
                    order_number = get_order_number(worksheet, empty_row)
                else:
                    order_number = None
                if empty_row and order_number:
                    threading.Thread(
                        target=track_position,
                        args=(worksheet, False, parsed_signal, empty_row, order_number, EXCHANGE),
                        daemon=True
                    ).start()
                    logger.info(f"Запущен трекинг для {parsed_signal.get('coin')} {parsed_signal.get('side')}")
            except Exception as e:
                logger.exception(f"Ошибка при запуске трекинга: {e}")


dp.include_router(router)


async def on_startup(app: web.Application) -> None:
    global worker_task, worksheet

    worksheet = init_gspread_client()
    if worksheet is None:
        logger.critical("Не удалось инициализировать Google Sheets. Бот запущен без таблицы.")
    else:
        try:
            old_orders = get_old_orders(worksheet)
            if old_orders:
                for old_order in old_orders:
                    threading.Thread(
                        target=track_position,
                        args=(worksheet, True, old_order, None, None, EXCHANGE),
                        daemon=True
                    ).start()
                logger.info(f"Запущен трекинг для {len(old_orders)} старых ордеров")
        except Exception as e:
            logger.exception(f"Ошибка при загрузке старых ордеров: {e}")

    await bot.set_webhook(WEBHOOK_URL)
    worker_task = asyncio.create_task(worker())
    logger.info("Webhook is set: %s", WEBHOOK_URL)


async def on_shutdown(app: web.Application) -> None:
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

    await bot.delete_webhook(drop_pending_updates=False)
    await bot.session.close()


async def handle(request: web.Request) -> web.Response:
    data = await request.json()
    await dp.feed_raw_update(bot, data)
    return web.Response(text="ok")


def main() -> None:
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    web.run_app(app, host="0.0.0.0", port=WEBHOOK_PORT)


if __name__ == "__main__":
    from utils.logger_setup import logger
    logger.info("Запуск CryptoSignalTableBot...")
    main()
