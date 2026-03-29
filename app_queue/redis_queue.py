import json
import logging
from collections import deque
from threading import Lock
from typing import Any

import redis

from bot.config import REDIS_URL, TELEGRAM_QUEUE_NAME

_fallback_queue: deque[dict[str, Any]] = deque()
_fallback_lock = Lock()


def _get_client() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)


def push(data: dict[str, Any]) -> None:
    try:
        client = _get_client()
        client.rpush(TELEGRAM_QUEUE_NAME, json.dumps(data, ensure_ascii=False))
    except Exception as exc:  # noqa: BLE001
        logging.exception("Redis push failed, use in-memory fallback: %s", exc)
        with _fallback_lock:
            _fallback_queue.append(data)


def pop() -> dict[str, Any] | None:
    try:
        client = _get_client()
        item = client.lpop(TELEGRAM_QUEUE_NAME)
        if item:
            return json.loads(item)
    except Exception as exc:  # noqa: BLE001
        logging.exception("Redis pop failed, trying in-memory fallback: %s", exc)

    with _fallback_lock:
        if _fallback_queue:
            return _fallback_queue.popleft()
    return None
