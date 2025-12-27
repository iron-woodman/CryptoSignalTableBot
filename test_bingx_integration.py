#!/usr/bin/env python3
"""
Тестовый скрипт для проверки интеграции с BingX WebSocket API
"""
import threading
import time
from queue import Queue
from utils.get_bingx_data import websocket_bingx
from utils.logger_setup import logger


def test_bingx_websocket():
    """
    Тестирует подключение к WebSocket API BingX
    """
    print("Запуск тестирования подключения к BingX WebSocket API...")
    
    # Создаем очередь для получения цен
    price_queue = Queue()
    subscribers = [price_queue]
    
    # Запускаем WebSocket соединение в отдельном потоке
    coin = "BTCUSDT"  # Используем популярную пару для тестирования
    ws_thread = threading.Thread(target=websocket_bingx, args=(coin, subscribers), daemon=True)
    ws_thread.start()
    
    print(f"Запущено WebSocket соединение для {coin}")
    
    # Ждем получения цен в течение 30 секунд
    start_time = time.time()
    timeout = 30  # 30 секунд таймаута
    
    while time.time() - start_time < timeout:
        if not price_queue.empty():
            price = price_queue.get()
            print(f"Получена цена от BingX: {price}")
            # Получили хотя бы одну цену, тест успешен
            print("✓ Тест подключения к BingX WebSocket API пройден успешно!")
            return True
        time.sleep(1)
    
    print("✗ Таймаут: не удалось получить цену от BingX за 30 секунд")
    return False


def test_signal_parsing():
    """
    Тестирует парсинг сигналов с указанием биржи BingX
    """
    print("\nЗапуск тестирования парсинга сигналов с указанием биржи BingX...")
    
    from utils.tg_signal2 import parse_signal_data2
    
    # Пример сигнала с указанием биржи BingX
    test_signal = """🚀 #BTCUSDT [LONG]
    
    Entry: 45000.00
    
    Take-Profit:
    1) 46000.00 (Target 1)
    2) 47000.00 (Target 2)
    3) 48000.00 (Target 3)
    4) 49000.00 (Target 4)
    5) 50000.00 (Target 5)
    
    Stop-loss: 44000.00
    
    Trade on BingX"""
    
    parsed_signal = parse_signal_data2(test_signal)
    
    if parsed_signal:
        print(f"Парсинг сигнала прошел успешно: {parsed_signal}")
        
        # Проверяем, что биржа определена правильно
        if parsed_signal.get('exchange') == 'bingx':
            print("✓ Тест парсинга сигнала с указанием биржи BingX пройден успешно!")
            return True
        else:
            print(f"✗ Биржа не определена правильно. Ожидается 'bingx', получено '{parsed_signal.get('exchange')}'")
            return False
    else:
        print("✗ Не удалось распарсить сигнал")
        return False


def main():
    """
    Основная функция тестирования
    """
    print("Тестирование интеграции с BingX для CryptoSignalTableBot\n")
    
    success_count = 0
    total_tests = 2
    
    # Тест 1: Подключение к WebSocket
    if test_bingx_websocket():
        success_count += 1
    
    # Тест 2: Парсинг сигналов
    if test_signal_parsing():
        success_count += 1
    
    # Результаты
    print(f"\nРезультаты тестирования:")
    print(f"Пройдено тестов: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 Все тесты пройдены! Интеграция с BingX работает корректно.")
        return True
    else:
        print("❌ Не все тесты пройдены. Проверьте конфигурацию интеграции с BingX.")
        return False


if __name__ == "__main__":
    main()