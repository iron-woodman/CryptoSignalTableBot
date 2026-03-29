import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def async_retry(
    func: Callable[[], Awaitable[T]],
    retries: int = 5,
    base_delay: float = 1.0,
) -> T:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return await func()
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            delay = base_delay * (2**attempt)
            logging.warning("Retry %s/%s failed: %s", attempt + 1, retries, exc)
            await asyncio.sleep(delay)

    raise RuntimeError("Max retries exceeded") from last_error
