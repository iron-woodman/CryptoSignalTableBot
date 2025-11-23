import time
import requests
from queue import Queue
from config import TOKEN, CHANNEL_NAME, TECH_CHANNEL_NAME, AV_CHANNEL_NAME
from .logger_setup import logger

# --- Глобальные переменные ---
queue_telegram = Queue()  # Очередь для хранения сигналов из Telegram
telegram_status = False  # Статус подключения к Telegram API
is_telegram_checked = False  # Флаг для отслеживания первой проверки подключения


def get_updates():
    """
    Получает последние обновления от Telegram API.

    Returns:
        dict: JSON-ответ от API Telegram.
    """
    global telegram_status, is_telegram_checked
    try:
        url = f'https://api.telegram.org/bot{TOKEN}/getUpdates?offset=-1'
        response = requests.get(url)
        if not telegram_status:
            telegram_status = True
            is_telegram_checked = True
            send_tech_alert('Подключились к Telegram API ✅')
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f'Не смог получить данные от телеграма: {e}, пробую еще раз..')
        if telegram_status or not is_telegram_checked:
            telegram_status = False
            is_telegram_checked = True
            send_tech_alert('Не смог получить данные от Telegram API ❌')


def parse_signal_data(new_signal):
    """
    Разбирает текстовый сигнал и преобразует его в словарь.

    Args:
        new_signal (str): Текст сигнала из Telegram.

    Returns:
        dict: Словарь с данными сигнала (монета, направление, TP, SL).
    """
    try:
        signal_dict = dict()
        lines = new_signal.split("\n")
        side = lines[0].split(": ")[0]
        coin = lines[0].split(": ")[1]
        targets = lines[3]
        targets = targets[6:].split(" >> ")
        stop_loss = float(lines[4].split(": ")[1].strip().rstrip('.'))

        signal_dict['coin'] = coin
        signal_dict['side'] = side
        for i, tp in enumerate(targets):
            signal_dict[f'tp{i + 1}'] = float(tp.split(' ')[0].strip().rstrip('.'))
        signal_dict['sl'] = stop_loss
        return signal_dict
    except IndexError:
        logger.error(f'Не смог распарсить сигнал:\n{new_signal}')
    except Exception as e:
        logger.error(f'Ошибка в parse_signal_data(): {e}')


def get_signal():
    """
    В бесконечном цикле опрашивает Telegram API на наличие новых сигналов.
    При появлении нового сигнала, парсит его и кладет в очередь.
    """
    last_update_id = 0
    is_first_check = True

    while True:
        try:
            time.sleep(0.9)
            update = get_updates()
            if not update or not update.get('result'):
                continue

            # Получаем ID последнего обновления
            current_update = update['result'][0]
            new_update_id = current_update['update_id']

            # При первом запуске просто сохраняем ID
            if is_first_check:
                is_first_check = False
                last_update_id = new_update_id
                continue

            # Если появилось новое обновление
            if new_update_id != last_update_id:
                last_update_id = new_update_id
                if 'channel_post' in current_update and 'text' in current_update['channel_post']:
                    signal_text = current_update['channel_post']['text']
                    parsed_signal = parse_signal_data(signal_text)
                    if parsed_signal:
                        queue_telegram.put(parsed_signal)

        except Exception as e:
            logger.error(f'Ошибка в get_signal(): {e}')


def send_alert(msg: str):
    """
    Отправляет сообщение в основной канал.

    Args:
        msg (str): Текст сообщения.
    """
    for _ in range(30):
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            params = {"chat_id": CHANNEL_NAME, "text": msg}
            r = requests.post(url, data=params)
            if r.status_code == 200:
                logger.info('Отправил уведомление в телеграм')
                break
            else:
                logger.error("Ошибка отсылки сообщения в телеграм")
                time.sleep(5)
        except Exception as e:
            logger.error(f'Ошибка в send_alert: {e}')
            time.sleep(2)


def send_av_alert(msg: str):
    """
    Отправляет сообщение в канал для усреднений.

    Args:
        msg (str): Текст сообщения.
    """
    for _ in range(30):
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            params = {"chat_id": AV_CHANNEL_NAME, "text": msg}
            r = requests.post(url, data=params)
            if r.status_code == 200:
                logger.info('Отправил уведомление об усреднении в телеграм')
                break
            else:
                logger.error("Ошибка отсылки сообщения об усреднении в телеграм")
                time.sleep(5)
        except Exception as e:
            logger.error(f'Ошибка в send_av_alert: {e}')
            time.sleep(2)


def send_tech_alert(msg: str):
    """
    Отправляет техническое сообщение (логирует его).
    Изначально была отправка в отдельный канал, но заменена на логирование.

    Args:
        msg (str): Текст сообщения.
    """
    try:
        logger.info(msg)
    except Exception as e:
        logger.error(f'Ошибка в send_tech_alert: {e}')
        time.sleep(2)
