import threading
import time
from utils import *


def main():
    """
    Основная функция запуска бота.
    Инициализирует и запускает все необходимые процессы в отдельных потоках.
    """
    try:

        threading.Thread(target=run_api).start()
        time.sleep(6)
        # Запуск потока для получения сигналов из Telegram
        threading.Thread(target=get_signal).start()
        logger.info("Bot started")
        print("Bot started")

        # Получение необработанных ордеров из Google таблицы
        old_data_orders, worksheet = get_old_orders()
        # Определение следующей свободной строки в таблице
        empty_row = get_empty_row(worksheet)
        # Определение номера для нового ордера
        order_number = get_order_number(worksheet, empty_row)
        # Создание генератора для получения номеров следующих ордеров и строк
        generate_row_order = row_order_iterator(empty_row, order_number)

        # Если есть необработанные ордера, запустить отслеживание для каждого из них
        if old_data_orders:
            for old_order in old_data_orders:
                threading.Thread(target=track_position, args=(True, old_order)).start()

        # Бесконечный цикл для обработки новых сигналов из Telegram
        while True:
            # Проверка наличия новых сигналов в очереди
            if not queue_telegram.empty():
                signal = queue_telegram.get()
                if signal is not None:
                    # Запуск отслеживания нового ордера в отдельном потоке
                    threading.Thread(target=track_position, args=(False, signal, empty_row, order_number)).start()
                    # Получение номера для следующего ордера
                    empty_row, order_number = next(generate_row_order)

    except KeyboardInterrupt as e:
        logger.exception(f'Завершенеи скрипта пользователем , {e}')
    except Exception as e:
        logger.exception(f'Ошибка в main() , {e}')


if __name__ == '__main__':
    logger.info("====================")
    print("====================")
    main()
