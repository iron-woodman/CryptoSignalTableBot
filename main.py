import threading
import time
import sys
from utils.logger_setup import logger
from utils.tg_signal import get_signal, queue_telegram
from utils.track_positions import track_position, row_order_iterator
from utils.check_status import run_api
from config import EXCHANGE

# Импортируем новый модуль и его функции
from utils.google_sheet  import (
    init_gspread_client,
    get_old_orders,
    get_empty_row,
    get_order_number
)


def main():
    """
    Основная функция запуска бота.
    Инициализирует и запускает все необходимые процессы в отдельных потоках.
    """
    # --- 1. Инициализация клиента Google Sheets ---
    # Этот шаг теперь выполняется один раз при запуске.
    worksheet = init_gspread_client()
    if worksheet is None:
        logger.critical("Не удалось инициализировать клиент Google Sheets. Завершение работы.")
        print("Не удалось инициализировать клиент Google Sheets. Завершение работы.")
        sys.exit(1) # Выход из скрипта, если подключение не удалось

    try:
        # --- 2. Запуск фоновых процессов ---
        threading.Thread(target=run_api, daemon=True).start()
        time.sleep(6)
        # Запуск потока для получения сигналов из Telegram
        threading.Thread(target=get_signal, daemon=True).start()
        logger.info("Bot started")
        print("Bot started")

        # --- 3. Получение начальных данных из таблицы ---
        # Все функции теперь принимают объект worksheet
        old_data_orders = get_old_orders(worksheet)
        empty_row = get_empty_row(worksheet)
        
        # Проверка, что удалось получить свободную строку
        if empty_row is None:
            logger.critical("Не удалось определить первую свободную строку. Завершение.")
            sys.exit(1)

        order_number = get_order_number(worksheet, empty_row)
        
        # Проверка, что номер ордера получен
        if order_number is None:
            logger.critical("Не удалось определить номер ордера. Завершение.")
            sys.exit(1)

        generate_row_order = row_order_iterator(empty_row, order_number)

        # --- 4. Запуск отслеживания для существующих ордеров ---
        if old_data_orders:
            for old_order in old_data_orders:
                # Передаем worksheet в поток для отслеживания
                # Используем биржу из настроек .env для всех ордеров
                threading.Thread(target=track_position, args=(worksheet, True, old_order, None, None, EXCHANGE), daemon=True).start()

        # --- 5. Основной цикл обработки новых сигналов ---
        while True:
            if not queue_telegram.empty():
                signal = queue_telegram.get()
                if signal is not None:
                    # Передаем worksheet в поток для отслеживания нового сигнала
                    # Используем биржу из настроек .env (она также дублируется в signal['exchange'], но берем глобальную для надежности)
                    threading.Thread(target=track_position, args=(worksheet, False, signal, empty_row, order_number, EXCHANGE), daemon=True).start()
                    empty_row, order_number = next(generate_row_order)
            
            time.sleep(1) # Небольшая пауза, чтобы не загружать CPU

    except KeyboardInterrupt:
        logger.info('Завершение скрипта пользователем.')
        print('Бот останавливается...')
    except Exception as e:
        logger.exception(f'Критическая ошибка в main(): {e}')



if __name__ == '__main__':
    logger.info("====================")
    print("====================")
    main()
