from typing import Any

from app_queue.redis_queue import push
from bot.config import CHAT_ID


def format_signal(signal: Any) -> str:
    if isinstance(signal, str):
        return signal

    if isinstance(signal, dict):
        coin = signal.get("coin", "UNKNOWN")
        side = signal.get("side", "UNKNOWN")
        sl = signal.get("sl", "-")
        tp_values = [
            str(signal[k])
            for k in sorted(signal.keys())
            if k.lower().startswith("tp")
        ]
        tp_line = ", ".join(tp_values) if tp_values else "-"
        return f"Signal: {coin} {side}\nTP: {tp_line}\nSL: {sl}"

    return f"Signal: {signal}"


def push_message(chat_id: str, text: str, parse_mode: str | None = None) -> None:
    payload: dict[str, Any] = {"chat_id": str(chat_id), "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    push(payload)


def process_signal(signal: Any, chat_id: str | None = None) -> None:
    destination = chat_id or CHAT_ID
    text = format_signal(signal)
    push_message(chat_id=destination, text=text)
