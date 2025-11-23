# Crypto Signal Table Bot

## Описание проекта

**Crypto Signal Table Bot** — это Telegram-бот, предназначенный для автоматического отслеживания торговых сигналов по криптовалютам. Бот получает сигналы из указанного Telegram-канала, отслеживает текущую цену актива через WebSocket с биржи Bybit и записывает все данные о сделках в Google-таблицу.

### Основной функционал:
- **Получение сигналов:** Бот мониторит Telegram-канал на предмет новых торговых сигналов.
- **Отслеживание цены:** Подключается к Bybit WebSocket для получения цены в реальном времени.
- **Ведение журнала сделок:** Вся информация по каждой сделке (цена входа, тейк-профиты, усреднения) записывается и обновляется в Google-таблице.
- **Уведомления:** Бот отправляет уведомления в Telegram о ключевых событиях:
    - Взятие тейк-профита.
    - Срабатывание ордера на усреднение.
    - Достижение точки безубытка.
    - Отклонение цены на 5% от точки входа (сигнал для ручного вмешательства).
- **Восстановление состояния:** После перезапуска бот может продолжать отслеживать незавершенные сделки, загружая их из Google-таблицы.

## Технологии
- **Язык:** Python 3.10+
- **Библиотеки:**
    - `python-telegram-bot` (или `requests` для прямого взаимодействия с API)
    - `gspread` (для работы с Google Sheets)
    - `websocket-client` (для подключения к Bybit)
    - `python-dotenv` (для управления конфигурацией)
- **База данных:** Google Sheets
- **Источник данных:** Bybit WebSocket API

## Инструкция по развертыванию на VPS (Ubuntu 22.04)

### 1. Подготовка сервера
1.  **Арендуйте VPS:** Выберите хостинг-провайдера и арендуйте сервер с Ubuntu 22.04 или новее.
2.  **Подключитесь к серверу по SSH:**
    ```bash
    ssh ваш_пользователь@ip_адрес_сервера
    ```
3.  **Обновите пакеты:**
    ```bash
    sudo apt update && sudo apt upgrade -y
    ```
4.  **Установите Python и необходимые утилиты:**
    ```bash
    sudo apt install python3 python3-pip python3-venv git -y
    ```

### 2. Клонирование проекта
1.  **Перейдите в домашнюю директорию:**
    ```bash
    cd ~
    ```
2.  **Клонируйте репозиторий с ботом:**
    ```bash
    git clone <URL_вашего_репозитория> CryptoSignalTableBot
    ```
3.  **Перейдите в директорию проекта:**
    ```bash
    cd CryptoSignalTableBot
    ```

### 3. Настройка окружения
1.  **Создайте виртуальное окружение:**
    ```bash
    python3 -m venv .venv
    ```
2.  **Активируйте виртуальное окружение:**
    ```bash
    source .venv/bin/activate
    ```
3.  **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```

### 4. Конфигурация
1.  **Настройте Google Sheets API:**
    - Следуйте [официальной инструкции gspread](https://docs.gspread.org/en/latest/oauth2.html) для создания сервис-аккаунта.
    - Скачайте JSON-файл с ключами.
    - Переименуйте его в `service_account.json` и поместите в корневую директорию проекта.
    - Не забудьте предоставить доступ сервис-аккаунту (email из JSON-файла) к вашей Google-таблице, выдав ему права редактора.
2.  **Создайте файл `.env`:**
    - Скопируйте файл-пример:
      ```bash
      cp .env.example .env
      ```
    - Откройте `.env` для редактирования:
      ```bash
      nano .env
      ```
    - Заполните все необходимые переменные:
      ```ini
      # Токен вашего Telegram-бота
      TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
      # ID канала для сигналов (можно получить у @userinfobot)
      CHANNEL_NAME="-1001234567890"
      # ID технического канала для отладки
      TECH_CHANNEL_NAME="-1001234567891"
      # ID канала для уведомлений об усреднениях
      AV_CHANNEL_NAME="-1001234567892"
      # Имя файла с ключом Google API
      GS_JS_FILE="service_account.json"
      # URL вашей Google таблицы
      GS_SHEET_FILE="https://docs.google.com/spreadsheets/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ.../edit#gid=0"
      # Номер листа в таблице (0 - первый)
      G_LIST="0"
      ```

### 5. Запуск и проверка
1.  **Запустите бота вручную для проверки:**
    ```bash
    python3 main.py
    ```
2.  **Проверьте, что бот запустился без ошибок.** В вашем техническом канале должны появиться сообщения о подключении к API.
3.  **Остановите бота, нажав `Ctrl+C`.**

### 6. Создание службы systemd
Чтобы бот работал в фоновом режиме и автоматически перезапускался, создадим для него службу `systemd`.

1.  **Создайте файл службы:**
    ```bash
    sudo nano /etc/systemd/system/crypto_bot.service
    ```
2.  **Вставьте в файл следующую конфигурацию:**
    - **Важно:** Замените `ваш_пользователь` на имя вашего пользователя на VPS.
    ```ini
    [Unit]
    Description=Crypto Signal Table Bot
    After=network.target

    [Service]
    User=ваш_пользователь
    Group=ваш_пользователь
    WorkingDirectory=/home/ваш_пользователь/CryptoSignalTableBot
    ExecStart=/home/ваш_пользователь/CryptoSignalTableBot/.venv/bin/python3 /home/ваш_пользователь/CryptoSignalTableBot/main.py
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
    ```
3.  **Сохраните файл и закройте редактор (`Ctrl+X`, `Y`, `Enter`).**

### 7. Управление службой
1.  **Перезагрузите конфигурацию `systemd`:**
    ```bash
    sudo systemctl daemon-reload
    ```
2.  **Включите автозапуск службы:**
    ```bash
    sudo systemctl enable crypto_bot.service
    ```
3.  **Запустите службу:**
    ```bash
    sudo systemctl start crypto_bot.service
    ```
4.  **Проверьте статус службы:**
    ```bash
    sudo systemctl status crypto_bot.service
    ```
    - Вы должны увидеть `active (running)`.
    - Если есть ошибки, просмотрите логи с помощью `journalctl -u crypto_bot -f`.

5.  **Чтобы остановить службу:**
    ```bash
    sudo systemctl stop crypto_bot.service
    ```
6.  **Чтобы перезапустить службу (например, после обновления кода):**
    ```bash
    sudo systemctl restart crypto_bot.service
    ```

Теперь ваш бот работает как служба, и будет автоматически запускаться после перезагрузки сервера.
