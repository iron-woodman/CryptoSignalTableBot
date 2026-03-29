import logging

from services.telegram.bot import bot
from utils.retry import async_retry


async def send_message(chat_id: str, text: str, parse_mode: str | None = None) -> None:
    async def _send() -> None:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)

    await async_retry(_send, retries=5)


async def send_task_message(task: dict) -> None:
    chat_id = str(task.get("chat_id", "")).strip()
    text = str(task.get("text", "")).strip()
    parse_mode = task.get("parse_mode")

    if not chat_id or not text:
        logging.warning("Skip invalid task payload: %s", task)
        return

    await send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
