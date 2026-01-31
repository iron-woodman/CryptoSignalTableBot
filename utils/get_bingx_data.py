import json
import time
import websocket
import gzip
import io
from utils.logger_setup import logger
from utils.tg_signal import send_tech_alert

# --- Управление состоянием ---
# Используем словарь для отслеживания состояния каждого WebSocket-соединения по монете
connection_states = {}


def create_on_message(subscribers, coin):
    """
    Фабричная функция для создания обработчика on_message.
    Этот обработчик будет вызываться при получении сообщения через WebSocket.

    Args:
        subscribers (list): Список очередей для добавления цен.
        coin (str): Название монеты для отслеживания состояния.

    Returns:
        function: Функция-обработчик on_message.
    """
    def on_message(ws, message):
        """
        Обрабатывает входящие сообщения от WebSocket.
        Извлекает цену и помещает ее в очереди подписчиков.
        """
        try:
            # Декомпрессия GZIP, если сообщение в байтах
            if isinstance(message, bytes):
                try:
                    with gzip.GzipFile(fileobj=io.BytesIO(message)) as f:
                        message = f.read().decode('utf-8')
                except OSError:
                    # Если это не GZIP, пробуем декодировать как обычный текст
                    message = message.decode('utf-8')

            # Игнорируем сообщения 'Ping' (сердцебиение от сервера)
            if message == 'Ping':
                # Можно отправить Pong в ответ, если библиотека не делает это сама
                # ws.send('Pong')
                return

            data = json.loads(message)
            
            # Проверяем на Ping в JSON формате (если есть)
            if isinstance(data, dict) and data.get('ping'):
                ws.send(json.dumps({'pong': data['ping']}))
                return

            # Проверяем формат сообщения от BingX
            # BingX может использовать разные форматы в зависимости от типа подписки
            last_price = None
            
            # Формат 1: {"stream":"symbol@ticker","data":{"e":"24hrTicker","s":"BTCUSDT","p":"-123.456","P":"-1.23","o":"10000.00","h":"10500.00","l":"9500.00","c":"9876.54","v":"1000.00","q":"1000000.00"}}
            if 'data' in data and 'c' in data['data']:  # 'c' - текущая цена
                last_price = float(data['data']['c'])
            # Альтернативный формат: {"symbol":"BTCUSDT","price":"9876.54"}
            elif 'price' in data:
                last_price = float(data['price'])
            # Формат с массивом данных
            elif 'data' in data and isinstance(data['data'], list):
                for item in data['data']:
                    if 'c' in item:
                        last_price = float(item['c'])
                        break
                    elif 'price' in item:
                        last_price = float(item['price'])
                        break
            
            if last_price is not None:
                # Рассылаем цену всем подписчикам
                # Используем копию списка, чтобы избежать проблем при изменении списка во время итерации
                for q in list(subscribers):
                    q.put(last_price)
                
                # Успешное получение данных подтверждает, что соединение установлено.
                if not connection_states.get(coin, {}).get('connected'):
                    logger.info(f"Первое сообщение получено от BingX Stream для {coin}. Соединение стабильно.")
                    connection_states[coin]['connected'] = True
                    send_tech_alert(f'Подключились к BingX Stream для {coin} ✅')
            else:
                # Если не удалось извлечь цену, логируем сообщение для отладки
                logger.debug(f"Получено сообщение от BingX без цены для {coin}: {message}")
        except json.JSONDecodeError:
            logger.error(f"Ошибка декодирования JSON от BingX для {coin}: {message}")
        except ValueError as e:
            logger.error(f"Ошибка преобразования цены от BingX для {coin}: {e}, сообщение: {message}")
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения от BingX для {coin}: {e}, сообщение: {message}")

    return on_message


def on_error(ws, error, coin):
    """
    Обработчик ошибок WebSocket.
    """
    logger.error(f"WebSocket error for {coin}: {error}")
    if connection_states.get(coin, {}).get('connected', True): # Отправляем алерт, если были подключены
        send_tech_alert(f'Отключились от BingX Stream для {coin} ❌')
    connection_states[coin] = {'connected': False}


def on_close(ws, close_status_code, close_msg, coin):
    """
    Обработчик закрытия соединения WebSocket.
    """
    logger.info(f"WebSocket for {coin} connection closed. Code: {close_status_code}, Msg: {close_msg}")
    if connection_states.get(coin, {}).get('connected', True): # Отправляем алерт, если были подключены
        send_tech_alert(f'Отключились от BingX Stream для {coin} ❌')
    connection_states[coin] = {'connected': False}


def create_on_open(coin):
    """
    Фабричная функция для создания обработчика on_open.
    Этот обработчик будет вызываться при открытии соединения WebSocket.

    Args:
        coin (str): Название монеты для подписки.

    Returns:
        function: Функция-обработчик on_open.
    """
    def on_open(ws):
        """
        Отправляет запрос на подписку тикеров для указанной монеты.
        """
        logger.info(f'Соединение с BingX Stream для {coin} открыто. Отправка подписки.')
        
        # Формат подписки для BingX WebSocket API (endpoint /market)
        # Пример: {"id":"id1", "reqType": "sub", "dataType": "BTC-USDT@ticker"}
        
        # Преобразуем формат пары, например BTCUSDT -> BTC-USDT
        formatted_coin = coin
        if coin.endswith("USDT") and "-" not in coin:
             formatted_coin = coin.replace("USDT", "-USDT")
        
        subscription_msg = {
            "id": "id1",
            "reqType": "sub",
            "dataType": f"{formatted_coin}@ticker"
        }
        
        ws.send(json.dumps(subscription_msg))
        
        # Не отправляем алерт здесь, ждем первого сообщения для подтверждения
        connection_states[coin] = {'connected': False} # Считаем подключенным после первого сообщения
    return on_open


def on_pong(ws, *data):
    """
    Обработчик pong-сообщений (для поддержания соединения).
    """
    logger.debug("Pong получен от BingX Stream.")


def on_ping(ws, *data):
    """
    Обработчик ping-сообщений.
    """
    logger.debug("Ping отправлен в BingX Stream.")


def websocket_bingx(coin, subscribers):
    """
    Основная функция для установки и поддержания WebSocket соединения с BingX.
    Использует экспоненциальную задержку для автоматического переподключения.

    Args:
        coin (str): Название монеты.
        subscribers (list): Список очередей для передачи цен.
    """
    reconnect_delay = 5  # Начальная задержка
    max_reconnect_delay = 120  # Максимальная задержка

    # Заголовки для имитации браузера (обход Cloudflare)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Origin": "https://bingx.com",
        "Accept-Language": "en-US,en;q=0.9",
    }

    while True:
        try:
            # Лямбда-функции для передачи дополнительных аргументов (coin)
            ws = websocket.WebSocketApp(
                "wss://open-api-ws.bingx.com/market",  # URL WebSocket API BingX для спотового рынка
                header=headers,
                on_message=create_on_message(subscribers, coin),
                on_error=lambda ws, error: on_error(ws, error, coin),
                on_close=lambda ws, code, msg: on_close(ws, code, msg, coin),
                on_ping=on_ping,
                on_pong=on_pong,
                on_open=create_on_open(coin)
            )
            # Сбрасываем задержку после успешного запуска
            reconnect_delay = 5
            logger.info(f"Запуск WebSocket для {coin}. Задержка сброшена на {reconnect_delay}с.")
            ws.run_forever(ping_interval=20, ping_timeout=10)

        except Exception as e:
            logger.exception(f'Критическая ошибка в websocket_bingx для {coin}: {e}')

        logger.warning(
            f"Соединение WebSocket для {coin} закрыто/не удалось. "
            f"Повторная попытка через {reconnect_delay} секунд."
        )
        send_tech_alert(
            f'Проблемы с подключением к BingX Stream для {coin}. '
            f'Повторная попытка через {reconnect_delay}с. ⏳'
        )
        time.sleep(reconnect_delay)
        # Увеличиваем задержку для следующей попытки
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)