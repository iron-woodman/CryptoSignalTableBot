import json
import time
import websocket
import gzip
import io
import threading
from utils.logger_setup import logger
from utils.tg_signal import send_tech_alert

class BingXWSManager:
    """
    Класс для управления единым WebSocket-соединением с BingX для множества монет.
    """
    def __init__(self):
        self.ws = None
        self.url = "wss://open-api-swap.bingx.com/swap-market"
        self.subscribers = {}  # { 'BTCUSDT': [queue1, queue2, ...] }
        self.connection_states = {} # { 'BTCUSDT': {'connected': False} }
        self.is_running = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 120
        self.lock = threading.Lock()

    def _get_formatted_coin(self, coin):
        if coin.endswith("USDT") and "-" not in coin:
            return coin.replace("USDT", "-USDT")
        return coin

    def _on_message(self, ws, message):
        try:
            if isinstance(message, bytes):
                try:
                    with gzip.GzipFile(fileobj=io.BytesIO(message)) as f:
                        message = f.read().decode('utf-8')
                except OSError:
                    message = message.decode('utf-8')

            if message == 'Ping':
                ws.send('Pong')
                return

            data = json.loads(message)
            
            if isinstance(data, dict) and data.get('ping'):
                ws.send(json.dumps({'pong': data['ping']}))
                return

            # Извлечение символа и цены
            coin = None
            last_price = None
            
            # BingX ticker data format
            if isinstance(data, dict) and 'data' in data and data['data']:
                inner_data = data['data']
                if isinstance(inner_data, dict):
                    # Пытаемся найти символ
                    s = inner_data.get('s')
                    if s:
                        coin = s.replace("-", "")
                    
                    # Пытаемся найти цену
                    if 'c' in inner_data:
                        last_price = float(inner_data['c'])
                elif isinstance(inner_data, list):
                    # Массив данных (может прийти при первой подписке или snapshot)
                    for item in inner_data:
                        s = item.get('s')
                        if s:
                            coin = s.replace("-", "")
                            if 'c' in item:
                                last_price = float(item['c'])
                                break

            if coin and last_price is not None:
                with self.lock:
                    if coin in self.subscribers:
                        for q in list(self.subscribers[coin]):
                            q.put(last_price)
                        
                        if not self.connection_states.get(coin, {}).get('connected'):
                            logger.info(f"Первое сообщение получено от BingX для {coin}. Соединение стабильно.")
                            self.connection_states[coin] = {'connected': True}
                            send_tech_alert(f'Подключились к BingX Futures Stream для {coin} ✅')
            elif isinstance(data, dict) and data.get('code'):
                 logger.error(f"Ошибка от BingX: {data}")

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения от BingX: {e}")

    def _on_error(self, ws, error):
        logger.error(f"BingX WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"BingX WebSocket closed. Code: {close_status_code}, Msg: {close_msg}")
        with self.lock:
            for coin in self.connection_states:
                if self.connection_states[coin].get('connected'):
                    send_tech_alert(f'Отключились от BingX Futures Stream для {coin} ❌')
                self.connection_states[coin] = {'connected': False}

    def _on_open(self, ws):
        logger.info('Соединение с BingX Futures Stream открыто.')
        self.reconnect_delay = 5
        with self.lock:
            for coin in self.subscribers:
                self._subscribe_coin(coin)

    def _subscribe_coin(self, coin):
        if self.ws and self.ws.sock and self.ws.sock.connected:
            formatted_coin = self._get_formatted_coin(coin)
            subscription_msg = {
                "id": f"sub_{coin}",
                "reqType": "sub",
                "dataType": f"{formatted_coin}@ticker"
            }
            self.ws.send(json.dumps(subscription_msg))
            logger.info(f"Отправлена подписка на {coin}")

    def add_subscriber(self, coin, queue):
        with self.lock:
            if coin not in self.subscribers:
                self.subscribers[coin] = []
                self.connection_states[coin] = {'connected': False}
                self._subscribe_coin(coin)
            self.subscribers[coin].append(queue)
            
    def remove_subscriber(self, coin, queue):
        with self.lock:
            if coin in self.subscribers:
                if queue in self.subscribers[coin]:
                    self.subscribers[coin].remove(queue)
                # Мы не отписываемся от монеты на уровне WS, чтобы не усложнять, 
                # просто перестаем слать данные в эту очередь.

    def run(self):
        self.is_running = True
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Origin": "https://bingx.com",
        }
        while self.is_running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                    header=headers
                )
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                logger.exception(f"Критическая ошибка в BingXWSManager: {e}")
            
            if self.is_running:
                logger.warning(f"Переподключение BingX через {self.reconnect_delay}с...")
                time.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

# Глобальный экземпляр менеджера
bingx_manager = BingXWSManager()
bingx_thread = None

def websocket_bingx(coin, subscribers):
    """
    Совместимая обертка для старого кода.
    """
    global bingx_thread
    if bingx_thread is None or not bingx_thread.is_alive():
        bingx_thread = threading.Thread(target=bingx_manager.run, daemon=True)
        bingx_thread.start()
    
    # subscribers здесь - это список из одной очереди, переданный из track_positions
    for q in subscribers:
        bingx_manager.add_subscriber(coin, q)
    
    # Чтобы не завершать поток (старый код ожидал, что эта функция блокирующая)
    while True:
        time.sleep(10)
