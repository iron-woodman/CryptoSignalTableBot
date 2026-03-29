# 🚀 PROJECT.MD — Полный рефактор CryptoSignalTableBot (для GPT-5.1 Codex)

## 🎯 ЦЕЛЬ

Полностью переработать проект **CryptoSignalTableBot** из нестабильного синхронного скрипта в **production-ready сервис**, устойчивый к:

* сетевым сбоям
* таймаутам Telegram API
* блокировкам / деградации соединений
* падениям WebSocket

---

## 🔥 КЛЮЧЕВАЯ АРХИТЕКТУРА (ЦЕЛЕВАЯ)

### ❌ Было:

WebSocket → логика → Telegram API (напрямую) → 💥 падения

### ✅ Стало:

WebSocket → обработка → Redis очередь → async worker → Telegram (webhook)

---

## 📦 ШАГ 1 — УСТАНОВКА ЗАВИСИМОСТЕЙ

```bash
pip install aiogram aiohttp redis python-dotenv
```

---

## 🗂 ШАГ 2 — НОВАЯ СТРУКТУРА ПРОЕКТА

Создать структуру:

```
bot/
  main.py
  config.py

core/
  signal_processor.py

services/
  telegram/
    bot.py
    sender.py

queue/
  redis_queue.py

workers/
  telegram_worker.py

integrations/
  bingx_ws.py

utils/
  retry.py
```

---

## ⚙️ ШАГ 3 — CONFIG

Создать `bot/config.py`:

```python
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

REDIS_URL = "redis://localhost:6379/0"

WEBHOOK_HOST = "https://YOUR_DOMAIN_OR_NGROK"
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = WEBHOOK_HOST + WEBHOOK_PATH
```

---

## 🔁 ШАГ 4 — RETRY (устойчивость сети)

Создать `utils/retry.py`:

```python
import asyncio
import logging

async def async_retry(func, retries=5):
    for attempt in range(retries):
        try:
            return await func()
        except Exception as e:
            delay = 2 ** attempt
            logging.warning(f"Retry {attempt}: {e}")
            await asyncio.sleep(delay)
    raise Exception("Max retries exceeded")
```

---

## 📦 ШАГ 5 — REDIS ОЧЕРЕДЬ

Создать `queue/redis_queue.py`:

```python
import redis
import json
from bot.config import REDIS_URL

r = redis.from_url(REDIS_URL)

QUEUE_NAME = "telegram_queue"

def push(data):
    r.rpush(QUEUE_NAME, json.dumps(data))

def pop():
    item = r.lpop(QUEUE_NAME)
    if item:
        return json.loads(item)
    return None
```

---

## 🤖 ШАГ 6 — TELEGRAM (ASYNC)

### `services/telegram/bot.py`

```python
from aiogram import Bot
from bot.config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
```

---

### `services/telegram/sender.py`

```python
import asyncio
import logging
from services.telegram.bot import bot

async def send_message(chat_id, text):
    for attempt in range(5):
        try:
            await bot.send_message(chat_id, text)
            return
        except Exception as e:
            delay = 2 ** attempt
            logging.warning(f"Retry {attempt}: {e}")
            await asyncio.sleep(delay)
```

---

## 🧵 ШАГ 7 — WORKER

Создать `workers/telegram_worker.py`:

```python
import asyncio
import logging
from queue.redis_queue import pop
from services.telegram.sender import send_message

async def worker():
    while True:
        item = pop()

        if not item:
            await asyncio.sleep(1)
            continue

        try:
            await send_message(item["chat_id"], item["text"])
            await asyncio.sleep(0.3)
        except Exception as e:
            logging.error(f"Worker error: {e}")
```

---

## 🧠 ШАГ 8 — SIGNAL PROCESSOR

Создать `core/signal_processor.py`:

```python
from queue.redis_queue import push
from bot.config import CHAT_ID

def process_signal(signal):
    text = format_signal(signal)

    push({
        "chat_id": CHAT_ID,
        "text": text
    })

def format_signal(signal):
    return f"🚀 {signal}"
```

---

## 🔌 ШАГ 9 — WEBSOCKET УСТОЙЧИВОСТЬ

Создать `integrations/bingx_ws.py`:

```python
import time
import logging
from core.signal_processor import process_signal

def run_ws(connect_func):
    while True:
        try:
            connect_func(process_signal)
        except Exception as e:
            logging.error(f"WS error: {e}")
            time.sleep(5)
```

---

## 🌐 ШАГ 10 — WEBHOOK ВМЕСТО POLLING

Создать `bot/main.py`:

```python
import asyncio
import logging
from aiohttp import web
from aiogram import Dispatcher

from services.telegram.bot import bot
from workers.telegram_worker import worker
from bot.config import WEBHOOK_PATH, WEBHOOK_URL

dp = Dispatcher()

async def on_startup(app):
    await bot.set_webhook(WEBHOOK_URL)
    asyncio.create_task(worker())

async def on_shutdown(app):
    await bot.delete_webhook()

async def handle(request):
    data = await request.json()
    await dp.feed_raw_update(bot, data)
    return web.Response()

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    web.run_app(app, port=8000)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
```

---

## 🔴 ШАГ 11 — УДАЛИТЬ СТАРУЮ ЛОГИКУ

Полностью удалить:

* polling (`getUpdates`)
* прямые вызовы Telegram API через requests
* синхронные send_message
* бесконечные while с логикой + Telegram внутри

---

## 🔁 ШАГ 12 — ЗАМЕНА ВЫЗОВОВ TELEGRAM

### ❌ Было:

```python
bot.send_message(chat_id, text)
```

### ✅ Стало:

```python
process_signal(signal)
```

или:

```python
push({
  "chat_id": chat_id,
  "text": text
})
```

---

## 🧪 ШАГ 13 — ЗАПУСК

```bash
redis-server
python bot/main.py
```

---

## 🌍 ШАГ 14 — WEBHOOK (ngrok)

```bash
ngrok http 8000
```

Вставить URL в:

```python
WEBHOOK_HOST
```

---

## ⚠️ ДОПОЛНИТЕЛЬНЫЕ УЛУЧШЕНИЯ

### 1. Увеличить таймауты (если останутся requests)

```
timeout=(5, 60)
```

### 2. Обработка DNS ошибок

* retry при `getaddrinfo failed`

### 3. Rate limit

```
sleep(0.3–0.5)
```

### 4. Логирование

```
logging.exception(...)
```

---

## 🔥 РЕЗУЛЬТАТ

После выполнения:

* бот работает асинхронно
* Telegram не блокирует выполнение
* сообщения не теряются
* устойчив к сетевым сбоям
* масштабируем
* готов к продакшену

---

## 🚀 РЕКОМЕНДАЦИЯ (ВАЖНО)

Для максимальной стабильности:

* запускать на VPS вне РФ
* использовать домен вместо ngrok
* при необходимости добавить proxy

---

## ✅ ГОТОВО

Этот файл можно использовать напрямую в GPT-5.1 Codex или Gemini CLI для автоматического рефакторинга проекта.
