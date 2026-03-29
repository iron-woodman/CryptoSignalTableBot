import asyncio
import logging

from aiohttp import web
from aiogram import Dispatcher, Router, types

from bot.config import CHAT_ID, WEBHOOK_PATH, WEBHOOK_PORT, WEBHOOK_URL
from core.signal_processor import process_signal
from services.telegram.bot import bot
from utils.tg_signal2 import parse_signal_data2
from workers.telegram_worker import worker

dp = Dispatcher()
router = Router()
worker_task: asyncio.Task | None = None


@router.channel_post()
async def on_channel_post(message: types.Message) -> None:
    if not message.text:
        return

    parsed_signal = parse_signal_data2(message.text)
    if parsed_signal:
        process_signal(parsed_signal, chat_id=CHAT_ID)


dp.include_router(router)


async def on_startup(app: web.Application) -> None:
    global worker_task
    await bot.set_webhook(WEBHOOK_URL)
    worker_task = asyncio.create_task(worker())
    logging.info("Webhook is set: %s", WEBHOOK_URL)


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
    logging.basicConfig(level=logging.INFO)
    main()
