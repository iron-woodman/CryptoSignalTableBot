import json
import time
import websocket
from utils.logger_setup import logger
from utils.tg_signal import send_tech_alert

# --- Глобальные переменные ---
wss_status = False  # Статус подключения к WebSocket
is_wss_checked = False  # Флаг для отслеживания первой проверки подключения


def create_on_message(queue_bybit):
    """
    Фабричная функция для создания обработчика on_message.
    Этот обработчик будет вызываться при получении сообщения через WebSocket.

    Args:
        queue_bybit (Queue): Очередь для добавления цен.

    Returns:
        function: Функция-обработчик on_message.
    """
    def on_message(ws, message):
        """
        Обрабатывает входящие сообщения от WebSocket.
        Извлекает цену и помещает ее в очередь.
        """
        global wss_status, is_wss_checked
        data = json.loads(message)
        if 'data' in data and 'lastPrice' in data['data']:
            last_price = data['data']['lastPrice']
            queue_bybit.put(last_price)
            if not wss_status:
                wss_status = True
                is_wss_checked = True
                send_tech_alert('Подключились к Bybit Stream ✅')
    return on_message


def on_error(ws, error):
    """
    Обработчик ошибок WebSocket.
    """
    global wss_status, is_wss_checked
    logger.error(f"WebSocket error: {error}")
    if wss_status or not is_wss_checked:
        wss_status = False
        is_wss_checked = True
        send_tech_alert('Отключились от Bybit Stream ❌')
    time.sleep(2)


def on_close(ws, close_status_code, close_msg):
    """
    Обработчик закрытия соединения WebSocket.
    """
    global wss_status, is_wss_checked
    logger.info("WebSocket connection closed")
    if wss_status or not is_wss_checked:
        wss_status = False
        is_wss_checked = True
        send_tech_alert('Отключились от Bybit Stream ❌')
    time.sleep(2)


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
        global wss_status, is_wss_checked
        logger.info('Подключились к Bybit Stream ✅')
        ws.send(json.dumps({"op": "subscribe", "args": [f"tickers.{coin}"]}))
        if not wss_status:
            wss_status = True
            is_wss_checked = True
            send_tech_alert('Подключились к Bybit Stream ✅')
    return on_open


def on_pong(ws, *data):
    """
    Обработчик pong-сообщений (для поддержания соединения).
    """
    pass


def on_ping(ws, *data):
    """
    Обработчик ping-сообщений.
    """
    pass


def websocket_bybit(coin, queue_bybit):
    """
    Основная функция для установки и поддержания WebSocket соединения с Bybit.
    Запускается в бесконечном цикле для автоматического переподключения.

    Args:
        coin (str): Название монеты.
        queue_bybit (Queue): Очередь для передачи цен.
    """
    global wss_status, is_wss_checked
    while True:
        try:
            ws = websocket.WebSocketApp(
                "wss://stream.bybit.com/v5/public/linear",
                on_message=create_on_message(queue_bybit),
                on_error=on_error,
                on_close=on_close,
                on_ping=on_ping,
                on_pong=on_pong,
                on_open=create_on_open(coin)
            )
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except Exception as e:
            logger.exception(f'Ошибка в websocket_bybit: {e}')
            if wss_status or not is_wss_checked:
                wss_status = False
                is_wss_checked = True
                send_tech_alert('Не смог подключиться к Bybit Stream ❌')
            time.sleep(5) # Пауза перед попыткой переподключения
