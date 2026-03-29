import asyncio
import logging

from app_queue.redis_queue import pop
from services.telegram.sender import send_task_message


async def worker() -> None:
    while True:
        try:
            item = await asyncio.to_thread(pop)
            if not item:
                await asyncio.sleep(0.5)
                continue

            await send_task_message(item)
            await asyncio.sleep(0.3)
        except Exception as exc:  # noqa: BLE001
            logging.exception("Worker error: %s", exc)
            await asyncio.sleep(1.0)
