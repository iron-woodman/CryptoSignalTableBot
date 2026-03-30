# CryptoSignalTableBot

Асинхронный сервис для обработки крипто-сигналов и отправки сообщений в Telegram через очередь Redis.

## Новая архитектура

`WebSocket/входящий сигнал -> core.signal_processor -> Redis очередь -> async worker -> Telegram Bot API (webhook)`

Это убирает прямую отправку в Telegram из торговой логики, снижает риск потерь сообщений и повышает устойчивость при сетевых сбоях.

## Структура

```text
bot/
  main.py
  config.py

core/
  signal_processor.py

services/
  telegram/
    bot.py
    sender.py

app_queue/
  redis_queue.py

workers/
  telegram_worker.py

integrations/
  bingx_ws.py

utils/
  retry.py
```

## Быстрый старт

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Настройте переменные окружения:

```bash
cp .env.example .env
```

Минимально обязательные:
- `BOT_TOKEN`
- `CHAT_ID`
- `WEBHOOK_HOST`

3. Поднимите Redis:

```bash
redis-server
```

4. Запустите бота:

```bash
python main.py
```

5. Для локального webhook используйте ngrok:

```bash
ngrok http 8000
```

и вставьте URL в `WEBHOOK_HOST`.

## Тесты

Добавлены автотесты основных функций:
- парсинг входящих сигналов;
- формирование и постановка сообщений в очередь;
- retry-механизм;
- работа Redis-очереди и fallback в память.

Запуск:

```bash
pytest -q
```

## Установка на VPS (Nginx + Redis + Webhook)

Ниже пример для Ubuntu 22.04/24.04.

1. Подготовка сервера:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git nginx redis-server certbot python3-certbot-nginx
```

2. Клонирование и установка проекта:

```bash
cd /opt
sudo git clone <YOUR_REPO_URL> CryptoSignalTableBot
sudo chown -R root:root /opt/CryptoSignalTableBot
cd /opt/CryptoSignalTableBot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Настройка `.env`:

```bash
cp .env.example .env
nano .env
```

Минимально заполнить:
- `BOT_TOKEN`
- `CHAT_ID`
- `WEBHOOK_HOST=https://cryptotable.skobarev.ru`
- `WEBHOOK_PATH=/webhook`
- `WEBHOOK_PORT=8000`
- `REDIS_URL=redis://localhost:6379/0`

4. Включить и проверить Redis:

```bash
sudo systemctl enable redis-server
sudo systemctl restart redis-server
sudo systemctl status redis-server
redis-cli ping
```

Ожидаемый ответ: `PONG`.

5. Настройка Nginx (reverse proxy на бота):

Создайте файл `/etc/nginx/sites-available/cryptobot`:

```nginx
server {
    listen 80;
    server_name cryptotable.skobarev.ru;

    location /webhook {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Активируйте конфиг:

```bash
sudo ln -s /etc/nginx/sites-available/cryptobot /etc/nginx/sites-enabled/cryptobot
sudo nginx -t
sudo systemctl reload nginx
```

6. Выпустить SSL-сертификат (Let's Encrypt):

```bash
sudo certbot --nginx -d cryptotable.skobarev.ru
```

После этого `WEBHOOK_HOST` должен быть именно на `https://...`.

7. Запуск бота как systemd-сервиса:

Создайте `/etc/systemd/system/cryptobot.service`:

```ini
[Unit]
Description=CryptoSignalTableBot
After=network.target redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/CryptoSignalTableBot
EnvironmentFile=/opt/CryptoSignalTableBot/.env
ExecStart=/opt/CryptoSignalTableBot/.venv/bin/python /opt/CryptoSignalTableBot/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cryptobot
sudo systemctl start cryptobot
sudo systemctl status cryptobot
```

Логи:

```bash
sudo journalctl -u cryptobot -f
```

8. Проверка webhook:

```bash
curl -s "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

В `url` должен быть ваш домен и путь, например: `https://cryptotable.skobarev.ru/webhook`.

9. Рекомендуемая базовая безопасность:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

Не открывайте порт `8000` наружу: он должен быть доступен только локально через Nginx.

## Что изменено

- Убрана старая polling-модель Telegram (`getUpdates`) из рабочего контура.
- Убраны прямые синхронные `requests`-вызовы Telegram из отправки уведомлений.
- Добавлен retry-механизм для асинхронной отправки.
- Добавлен worker с rate-limit (`0.3s`) между сообщениями.
- Добавлена совместимость со старыми env-переменными (`TOKEN`, `CHANNEL_NAME` и др.).
