import logging
import time
from collections.abc import Callable

from core.signal_processor import process_signal


def run_ws(connect_func: Callable[[Callable], None]) -> None:
    while True:
        try:
            connect_func(process_signal)
        except Exception as exc:  # noqa: BLE001
            logging.exception("WS error: %s", exc)
            time.sleep(5)
