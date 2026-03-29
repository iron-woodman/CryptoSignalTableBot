import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID") or os.getenv("CHANNEL_NAME", "")
TECH_CHAT_ID = os.getenv("TECH_CHAT_ID") or os.getenv("TECH_CHANNEL_NAME", "")
AV_CHAT_ID = os.getenv("AV_CHAT_ID") or os.getenv("AV_CHANNEL_NAME", "")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
TELEGRAM_QUEUE_NAME = os.getenv("TELEGRAM_QUEUE_NAME", "telegram_queue")

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://YOUR_DOMAIN_OR_NGROK")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = f"{WEBHOOK_HOST.rstrip('/')}{WEBHOOK_PATH}"
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8000"))

EXCHANGE = os.getenv("EXCHANGE", "bybit").lower()
LOG_PONG_MESSAGES = os.getenv("LOG_PONG_MESSAGES", "False").lower() == "true"

GS_JS_FILE = os.getenv("GS_JS_FILE", "service_account.json")
GS_SHEET_FILE = os.getenv("GS_SHEET_FILE", "")
G_LIST = os.getenv("G_LIST", "0")

BINGX_API_KEY = os.getenv("BINGX_API_KEY", "")
BINGX_API_SECRET = os.getenv("BINGX_API_SECRET", "")
