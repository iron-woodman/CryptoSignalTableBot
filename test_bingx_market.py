import threading
import queue
import time
from utils.get_bingx_data import websocket_bingx
from loguru import logger
import sys

# Настройка логгера для вывода в консоль
logger.remove()
logger.add(sys.stderr, level="INFO")

def test_bingx_prices():
    """
    Тестовый скрипт для проверки получения цен с BingX для нескольких монет.
    """
    coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    price_queues = {coin: queue.Queue() for coin in coins}
    
    threads = []
    
    print(f"Запуск теста BingX для монет: {', '.join(coins)}")
    print("Ожидание первых данных (может занять несколько секунд)...")
    print("-" * 50)

    # Запуск потоков WebSocket для каждой монеты
    for coin in coins:
        t = threading.Thread(
            target=websocket_bingx, 
            args=(coin, [price_queues[coin]]), 
            daemon=True
        )
        t.start()
        threads.append(t)

    try:
        # Собираем цены в течение 30 секунд
        start_time = time.time()
        last_printed_prices = {coin: None for coin in coins}
        
        while time.time() - start_time < 30:
            for coin in coins:
                try:
                    # Пытаемся получить цену из очереди без блокировки
                    price = price_queues[coin].get_nowait()
                    if price != last_printed_prices[coin]:
                        print(f"[{time.strftime('%H:%M:%S')}] {coin}: {price}")
                        last_printed_prices[coin] = price
                except queue.Empty:
                    continue
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nТест прерван пользователем.")
    
    print("-" * 50)
    print("Тест завершен.")

if __name__ == "__main__":
    test_bingx_prices()
