from core.signal_processor import push_message
from bot.config import AV_CHAT_ID, CHAT_ID
from .logger_setup import logger


def send_alert(msg: str) -> None:
    push_message(chat_id=CHAT_ID, text=msg, parse_mode="HTML")
    logger.info("Queued alert for main channel")


def send_av_alert(msg: str) -> None:
    destination = AV_CHAT_ID or CHAT_ID
    push_message(chat_id=destination, text=msg)
    logger.info("Queued alert for averaging channel")


def send_tech_alert(msg: str) -> None:
    logger.info(msg)
