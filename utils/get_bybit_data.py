import json
import time
import websocket
import threading
from utils.logger_setup import logger
from utils.tg_signal import send_tech_alert

class BybitWSManager:
    """
    Класс для управления единым WebSocket-соединением с Bybit для множества монет.
    """
    def __init__(self):
        self.ws = None
        self.url = "wss://stream.bybit.com/v5/public/linear"
        self.subscribers = {}  # { 'BTCUSDT': [queue1, queue2, ...] }
        self.connection_states = {} # { 'BTCUSDT': {'connected': False} }
        self.is_running = False
        self.reconnect_delay = 5
        self.max_reconnect_delay = 120
        self.lock = threading.Lock()

    def _on_message(self, ws, message):
        try:
            data = json.loads(message)
            
            # Обработка данных тикера
            if 'data' in data and 'symbol' in data['data'] and 'lastPrice' in data['data']:
                coin = data['data']['symbol']
                last_price = float(data['data']['lastPrice'])
                
                with self.lock:
                    if coin in self.subscribers:
                        for q in list(self.subscribers[coin]):
                            q.put(last_price)
                        
                        if not self.connection_states.get(coin, {}).get('connected'):
                            logger.info(f"Первое сообщение получено от Bybit для {coin}. Соединение стабильно.")
                            self.connection_states[coin] = {'connected': True}
                            send_tech_alert(f'Подключились к Bybit Stream для {coin} ✅')
            
            # Bybit heartbeats (client-side ping is handled by run_forever, 
            # server-side ping is usually WS-level but can be JSON in some cases)
            if 'op' in data and data['op'] == 'ping':
                ws.send(json.dumps({"op": "pong"}))

        except Exception as e:
            logger.error(f"Ошибка обработки сообщения от Bybit: {e}")

    def _on_error(self, ws, error):
        logger.error(f"Bybit WebSocket error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        logger.info(f"Bybit WebSocket closed. Code: {close_status_code}, Msg: {close_msg}")
        with self.lock:
            for coin in self.connection_states:
                if self.connection_states[coin].get('connected'):
                    send_tech_alert(f'Отключились от Bybit Stream для {coin} ❌')
                self.connection_states[coin] = {'connected': False}

    def _on_open(self, ws):
        logger.info('Соединение с Bybit Stream открыто.')
        self.reconnect_delay = 5
        with self.lock:
            for coin in self.subscribers:
                self._subscribe_coin(coin)

    def _subscribe_coin(self, coin):
        if self.ws and self.ws.sock and self.ws.sock.connected:
            subscription_msg = {
                "op": "subscribe",
                "args": [f"tickers.{coin}"]
            }
            self.ws.send(json.dumps(subscription_msg))
            logger.info(f"Отправлена подписка Bybit на {coin}")

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

    def run(self):
        self.is_running = True
        while self.is_running:
            try:
                self.ws = websocket.WebSocketApp(
                    self.url,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open
                )
                self.ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as e:
                logger.exception(f"Критическая ошибка в BybitWSManager: {e}")
            
            if self.is_running:
                logger.warning(f"Переподключение Bybit через {self.reconnect_delay}с...")
                time.sleep(self.reconnect_delay)
                self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)

# Глобальный экземпляр менеджера
bybit_manager = BybitWSManager()
bybit_thread = None

def websocket_bybit(coin, subscribers):
    """
    Совместимая обертка для старого кода.
    """
    global bybit_thread
    if bybit_thread is None or not bybit_thread.is_alive():
        bybit_thread = threading.Thread(target=bybit_manager.run, daemon=True)
        bybit_thread.start()
    
    for q in subscribers:
        bybit_manager.add_subscriber(coin, q)
    
    while True:
        time.sleep(10)
