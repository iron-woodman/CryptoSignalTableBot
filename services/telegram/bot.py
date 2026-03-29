from aiogram import Bot

from bot.config import BOT_TOKEN

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")

bot = Bot(token=BOT_TOKEN)
