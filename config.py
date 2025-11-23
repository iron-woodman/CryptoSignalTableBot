import os
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# --- Настройки для Telegram ---
# Токен вашего Telegram-бота. Получается у @BotFather.
TOKEN = os.getenv('TOKEN', '')
# ID основного канала, куда бот будет отправлять сигналы о взятии TP.
CHANNEL_NAME = os.getenv('CHANNEL_NAME', '')
# ID технического канала для получения отладочной информации и сообщений об ошибках.
TECH_CHANNEL_NAME = os.getenv('TECH_CHANNEL_NAME', '')
# ID канала для уведомлений об усреднениях и достижении безубытка.
AV_CHANNEL_NAME = os.getenv('AV_CHANNEL_NAME', '')

# --- Настройки для Google Sheets ---
# Имя файла с ключом сервис-аккаунта Google API в формате JSON.
GS_JS_FILE = os.getenv('GS_JS_FILE', 'service_account.json')
# URL вашей Google таблицы, в которой бот будет хранить данные о сделках.
GS_SHEET_FILE = os.getenv('GS_SHEET_FILE', '')
# Номер листа в Google таблице, с которым будет работать бот (нумерация с 0).
G_LIST = os.getenv('G_LIST', '0')
