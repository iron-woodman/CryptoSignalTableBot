import time
import requests
from queue import Queue
from config import TOKEN, CHANNEL_NAME, TECH_CHANNEL_NAME, AV_CHANNEL_NAME, EXCHANGE
from .logger_setup import logger
from .tg_signal2 import parse_signal_data2

# --- Глобальные переменные ---
queue_telegram = Queue()  # Очередь для хранения сигналов из Telegram
telegram_status = False  # Статус подключения к Telegram API
is_telegram_checked = False  # Флаг для отслеживания первой проверки подключения


def get_updates(offset: int = None):
    """
    Получает последние обновления от Telegram API.

    Args:
        offset (int, optional): ID следующего ожидаемого обновления.
                                Если None — запрашиваем только последнее (offset=-1).

    Returns:
        dict: JSON-ответ от API Telegram.
    """
    global telegram_status, is_telegram_checked
    try:
        # Используем переданный offset чтобы не пропускать и не дублировать сообщения.
        # offset=-1 только при первом запросе, далее offset=last_update_id+1
        offset_param = offset if offset is not None else -1
        url = f'https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset_param}&timeout=10'
        response = requests.get(url, timeout=15)
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
        dict: Словарь с данными сигнала (монета, направление, TP, SL, exchange).
    """
    try:
        signal_dict = dict()
        
        # Используем глобальную настройку биржи
        signal_dict['exchange'] = EXCHANGE
        
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

    Исправления:
    - Используем offset=last_update_id+1, чтобы не читать одно и то же сообщение повторно.
    - Фильтруем сообщения только из канала-источника сигналов (CHANNEL_NAME).
      Это исключает ситуацию, когда бот читает собственные уведомления о TP/усреднениях
      и пытается распарсить их как торговые сигналы.
    """
    last_update_id = 0
    is_first_check = True

    while True:
        try:
            time.sleep(0.9)

            # При первом запуске берём offset=-1 чтобы узнать текущий update_id,
            # не обрабатывая старые сообщения. Далее всегда передаём offset=last_update_id+1.
            offset = None if is_first_check else last_update_id + 1
            update = get_updates(offset=offset)

            if not update or not update.get('result'):
                continue

            # При первом запуске просто сохраняем ID последнего апдейта и выходим
            if is_first_check:
                is_first_check = False
                last_update_id = update['result'][-1]['update_id']
                continue

            # Обрабатываем все новые обновления из результата
            for current_update in update['result']:
                new_update_id = current_update['update_id']
                last_update_id = new_update_id  # сдвигаем указатель

                if 'channel_post' not in current_update:
                    continue
                post = current_update['channel_post']
                if 'text' not in post:
                    continue

                # Фильтр по chat_id: обрабатываем только сообщения из канала с сигналами.
                # Бот сам пишет уведомления в CHANNEL_NAME — они не должны парситься как сигналы.
                post_chat_id = str(post.get('chat', {}).get('id', ''))
                source_channel = str(CHANNEL_NAME)
                if post_chat_id and post_chat_id != source_channel:
                    logger.debug(f"Пропускаем сообщение из чата {post_chat_id} (ожидается {source_channel})")
                    continue

                signal_text = post['text']
                parsed_signal = parse_signal_data2(signal_text)
                if parsed_signal:
                    logger.info(f"Сигнал принят в очередь: {parsed_signal['coin']} {parsed_signal['side']}")
                    queue_telegram.put(parsed_signal)

        except Exception as e:
            logger.error(f'Ошибка в get_signal(): {e}')


def send_alert(msg: str):
    """
    Отправляет сообщение в основной канал в формате HTML.

    Args:
        msg (str): Текст сообщения (может содержать HTML-теги).
    """
    for _ in range(30):
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            params = {"chat_id": CHANNEL_NAME, "text": msg, "parse_mode": "HTML"}
            r = requests.post(url, data=params)
            if r.status_code == 200:
                logger.info('Отправил уведомление в телеграм')
                break
            else:
                logger.error(f"Ошибка отсылки сообщения в телеграм (chat_id={CHANNEL_NAME}): {r.status_code} - {r.text}")
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
                logger.error(f"Ошибка отсылки сообщения об усреднении в телеграм (chat_id={AV_CHANNEL_NAME}): {r.status_code} - {r.text}")
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
