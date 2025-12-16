import json
import time
import websocket
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
        data = json.loads(message)
        if 'data' in data and 'lastPrice' in data['data']:
            last_price = data['data']['lastPrice']
            # Рассылаем цену всем подписчикам
            # Используем копию списка, чтобы избежать проблем при изменении списка во время итерации
            for q in list(subscribers):
                q.put(last_price)
            
            # Успешное получение данных подтверждает, что соединение установлено.
            if not connection_states.get(coin, {}).get('connected'):
                logger.info(f"Первое сообщение получено от Bybit Stream для {coin}. Соединение стабильно.")
                connection_states[coin]['connected'] = True
                send_tech_alert(f'Подключились к Bybit Stream для {coin} ✅')

    return on_message


def on_error(ws, error, coin):
    """
    Обработчик ошибок WebSocket.
    """
    logger.error(f"WebSocket error for {coin}: {error}")
    if connection_states.get(coin, {}).get('connected', True): # Отправляем алерт, если были подключены
        send_tech_alert(f'Отключились от Bybit Stream для {coin} ❌')
    connection_states[coin] = {'connected': False}


def on_close(ws, close_status_code, close_msg, coin):
    """
    Обработчик закрытия соединения WebSocket.
    """
    logger.info(f"WebSocket for {coin} connection closed. Code: {close_status_code}, Msg: {close_msg}")
    if connection_states.get(coin, {}).get('connected', True): # Отправляем алерт, если были подключены
        send_tech_alert(f'Отключились от Bybit Stream для {coin} ❌')
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
        logger.info(f'Соединение с Bybit Stream для {coin} открыто. Отправка подписки.')
        ws.send(json.dumps({"op": "subscribe", "args": [f"tickers.{coin}"]}))
        # Не отправляем алерт здесь, ждем первого сообщения для подтверждения
        connection_states[coin] = {'connected': False} # Считаем подключенным после первого сообщения
    return on_open


def on_pong(ws, *data):
    """
    Обработчик pong-сообщений (для поддержания соединения).
    """
    logger.debug("Pong получен от Bybit Stream.")


def on_ping(ws, *data):
    """
    Обработчик ping-сообщений.
    """
    logger.debug("Ping отправлен в Bybit Stream.")


def websocket_bybit(coin, subscribers):
    """
    Основная функция для установки и поддержания WebSocket соединения с Bybit.
    Использует экспоненциальную задержку для автоматического переподключения.

    Args:
        coin (str): Название монеты.
        subscribers (list): Список очередей для передачи цен.
    """
    reconnect_delay = 5  # Начальная задержка
    max_reconnect_delay = 120  # Максимальная задержка

    while True:
        try:
            # Лямбда-функции для передачи дополнительных аргументов (coin)
            ws = websocket.WebSocketApp(
                "wss://stream.bybit.com/v5/public/linear",
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
            logger.exception(f'Критическая ошибка в websocket_bybit для {coin}: {e}')

        logger.warning(
            f"Соединение WebSocket для {coin} закрыто/не удалось. "
            f"Повторная попытка через {reconnect_delay} секунд."
        )
        send_tech_alert(
            f'Проблемы с подключением к Bybit Stream для {coin}. '
            f'Повторная попытка через {reconnect_delay}с. ⏳'
        )
        time.sleep(reconnect_delay)
        # Увеличиваем задержку для следующей попытки
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
