# -*- coding: utf-8 -*-
import time
import gspread
from .logger_setup import logger
from config import GS_JS_FILE, GS_SHEET_FILE, G_LIST
from .tg_signal import send_tech_alert

# --- Константы ---
JS_FILE = GS_JS_FILE  # Имя файла с ключом Google API
SHEET_URL = GS_SHEET_FILE  # URL Google таблицы
LIST_NUMBER = int(G_LIST)  # Номер листа в таблице
MAX_RETRIES = 5 # Максимальное количество попыток при ошибках API
RETRY_DELAY = 10 # Задержка между попытками в секундах

def init_gspread_client():
    """
    Инициализирует и возвращает клиент gspread и рабочий лист.

    Эта функция должна вызываться один раз при старте приложения.
    Она пытается подключиться к Google Sheets с несколькими попытками.

    Returns:
        gspread.Worksheet | None: Объект рабочего листа или None в случае неудачи.
    """
    logger.info("Попытка подключения к Google Sheets API...")
    for i in range(MAX_RETRIES):
        try:
            gc = gspread.service_account(filename=JS_FILE)
            sh = gc.open_by_url(SHEET_URL)
            worksheet = sh.get_worksheet(LIST_NUMBER)
            logger.info("Успешное подключение к Google Sheets API.")
            send_tech_alert('Подключились к Google API ✅')
            return worksheet
        except gspread.exceptions.APIError as e:
            logger.error(f'Ошибка API при подключении к Google Sheets (попытка {i + 1}/{MAX_RETRIES}): {e}')
            time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.exception(f'Непредвиденная ошибка при подключении к Google Sheets (попытка {i + 1}/{MAX_RETRIES}): {e}')
            time.sleep(RETRY_DELAY)

    logger.error("Не удалось подключиться к Google Sheets API после нескольких попыток.")
    send_tech_alert('Критическая ошибка: не удалось подключиться к Google API ❌')
    return None


def _execute_with_retry(worksheet_operation, *args, **kwargs):
    """
    Выполняет операцию с рабочим листом с логикой повторных попыток.
    Внутренняя функция-обертка.
    """
    for i in range(MAX_RETRIES):
        try:
            result = worksheet_operation(*args, **kwargs)
            return result
        except gspread.exceptions.APIError as e:
            logger.error(f'Ошибка API при выполнении операции {worksheet_operation.__name__} (попытка {i + 1}/{MAX_RETRIES}): {e}')
            time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.exception(f'Непредвиденная ошибка в {worksheet_operation.__name__} (попытка {i + 1}/{MAX_RETRIES}): {e}')
            time.sleep(RETRY_DELAY)
    logger.error(f"Не удалось выполнить операцию {worksheet_operation.__name__} после {MAX_RETRIES} попыток.")
    send_tech_alert(f'Ошибка запроса к Google API при операции {worksheet_operation.__name__} ❌')
    return None


def is_order(value):
    """
    Преобразует булево значение в символ для отображения в таблице.
    """
    return '➕' if value else '➖'


def get_empty_row(worksheet: gspread.Worksheet):
    """
    Находит номер первой свободной строки в таблице (оптимизировано).

    Args:
        worksheet (gspread.Worksheet): Рабочий лист Google таблицы.

    Returns:
        int | None: Номер первой свободной строки или None в случае ошибки.
    """
    logger.debug("Получение первой свободной строки...")
    # Используем col_values(1) для получения только первого столбца - это намного быстрее, чем get_all_values()
    col_a = _execute_with_retry(worksheet.col_values, 1)
    if col_a is not None:
        empty_row = len(col_a) + 1
        logger.debug(f"Найдена свободная строка: {empty_row}")
        return empty_row
    return None


def get_order_number(worksheet: gspread.Worksheet, empty_row: int):
    """
    Определяет порядковый номер для новой сделки.

    Args:
        worksheet (gspread.Worksheet): Рабочий лист Google таблицы.
        empty_row (int): Номер текущей свободной строки.

    Returns:
        int | None: Номер для новой сделки или None в случае ошибки.
    """
    if empty_row <= 2: # Если таблица пуста или есть только заголовок
        return 1
        
    logger.debug(f"Определение номера ордера для строки {empty_row}...")
    number = _execute_with_retry(worksheet.acell, f'A{empty_row - 1}').value
    if number is not None and number.isdigit():
        order_num = int(number) + 1
        logger.debug(f"Следующий номер ордера: {order_num}")
        return order_num
    elif number is None:
         # Если предыдущая ячейка пуста, ищем последнюю заполненную
        col_a = _execute_with_retry(worksheet.col_values, 1)
        if col_a:
            for i in range(len(col_a) - 1, 0, -1):
                if col_a[i] and col_a[i].isdigit():
                    return int(col_a[i]) + 1
        return 1 # Если в столбце А нет чисел
    else:
        return 1


def get_old_orders(worksheet: gspread.Worksheet):
    """
    Получает из таблицы все незавершенные сделки.

    Args:
        worksheet (gspread.Worksheet): Рабочий лист Google таблицы.

    Returns:
        list | None: Список незавершенных сделок или None в случае ошибки.
    """
    logger.info("Загрузка незавершенных ордеров из таблицы...")
    sheet_data = _execute_with_retry(worksheet.get_all_values)
    if sheet_data is None:
        return None

    live_trades = []
    for line in sheet_data:
        # Проверяем, что в строке достаточно столбцов и что 13-й столбец (индекс 12) равен '➕'
        if len(line) > 12 and line[12] == '➕':
            live_trades.append(line)
    
    logger.info(f"Найдено {len(live_trades)} незавершенных ордеров.")
    return live_trades


def gs_first_update(worksheet: gspread.Worksheet, coin, side, date_time, current_price, tp1, tp2, tp3, tp4, tp5, is_order_exist, empty_row, order_number):
    """
    Записывает в таблицу информацию о новой сделке.
    """
    gs_coin = coin.replace('/USDT', '')
    row_data = [order_number, gs_coin, side, date_time, current_price, tp1, tp2, tp3, tp4, tp5, '0', '', is_order(is_order_exist), '', '0', '', '➖']
    
    logger.info(f"Запись новой сделки в строку {empty_row}: {row_data}")
    result = _execute_with_retry(worksheet.update, f'A{empty_row}:Q{empty_row}', [row_data])
    if result:
        logger.info('Успешно записали новую сделку в таблицу.')
    return result


def gs_tp_update(worksheet: gspread.Worksheet, tp_count, empty_row):
    """
    Обновляет в таблице количество взятых тейк-профитов.
    """
    logger.info(f"Обновление TP={tp_count} для строки {empty_row}")
    # Сначала прочитаем значение, чтобы не делать лишнюю запись
    current_tp_in_gs = _execute_with_retry(worksheet.acell, f'O{empty_row}').value
    if current_tp_in_gs is not None and current_tp_in_gs.isdigit() and tp_count > int(current_tp_in_gs):
        result = _execute_with_retry(worksheet.update, f'O{empty_row}', [[tp_count]])
        if result:
            logger.info(f'Успешно обновили TP в таблице для строки {empty_row}.')
        return result
    elif current_tp_in_gs is None or not current_tp_in_gs.isdigit(): # если ячейка пустая или не число
        return _execute_with_retry(worksheet.update, f'O{empty_row}', [[tp_count]])
    else:
        logger.warning(f"Попытка обновить TP в таблице для строки {empty_row}, но новое значение ({tp_count}) не больше старого ({current_tp_in_gs}).")
        return None

def gs_final_tp_update(worksheet: gspread.Worksheet, tp_count, empty_row, is_order_exist):
    """
    Обновляет количество TP и закрывает сделку в таблице.
    """
    logger.info(f"Финальное обновление TP={tp_count} и закрытие сделки для строки {empty_row}")
    # Используем batch_update для выполнения нескольких операций за один API-вызов
    requests = [
        {'range': f'O{empty_row}', 'values': [[tp_count]]},
        {'range': f'M{empty_row}', 'values': [[is_order(is_order_exist)]]}
    ]
    result = _execute_with_retry(worksheet.batch_update, requests)
    if result:
        logger.info(f'Успешно закрыли сделку по TP в таблице для строки {empty_row}.')
    return result


def gs_stop_update(worksheet: gspread.Worksheet, stop_loss, empty_row, is_order_exist):
    """
    Обновляет статус сделки на 'закрыто по стопу' и записывает цену стоп-лосса.
    """
    logger.info(f"Обновление стоп-лосса и закрытие сделки для строки {empty_row}")
    requests = [
        {'range': f'M{empty_row}', 'values': [[is_order(is_order_exist)]]},
        {'range': f'P{empty_row}', 'values': [[stop_loss]]}
    ]
    result = _execute_with_retry(worksheet.batch_update, requests)
    if result:
        logger.info(f'Успешно закрыли сделку по стоп-лоссу в таблице для строки {empty_row}.')
    return result


def gs_av_update(worksheet: gspread.Worksheet, av_count, empty_row, av_order):
    """
    Обновляет в таблице количество усреднений и цену последнего усреднения.
    """
    logger.info(f"Обновление усреднения {av_count} для строки {empty_row}")
    requests = [
        {'range': f'K{empty_row}', 'values': [[av_count]]},
        {'range': f'L{empty_row}', 'values': [[av_order]]}
    ]
    result = _execute_with_retry(worksheet.batch_update, requests)
    if result:
        logger.info(f'Успешно обновили данные по усреднению в таблице для строки {empty_row}.')
    return result

def gs_breakeven_update(worksheet: gspread.Worksheet, empty_row, is_order_exist):
    """
    Обновляет статус сделки на 'закрыто по безубытку'.
    """
    logger.info(f"Обновление статуса на 'безубыток' для строки {empty_row}")
    requests = [
        {'range': f'M{empty_row}', 'values': [[is_order(is_order_exist)]]},
        {'range': f'N{empty_row}', 'values': [['✅']]}
    ]
    result = _execute_with_retry(worksheet.batch_update, requests)
    if result:
        logger.info(f'Успешно обновили статус на "безубыток" в таблице для строки {empty_row}.')
    return result


def gs_5_perc_alert_update(worksheet: gspread.Worksheet, empty_row):
    """
    Отмечает в таблице, что было отправлено уведомление о 5% отклонении цены.
    """
    logger.info(f"Установка флага '5% алерт' для строки {empty_row}")
    result = _execute_with_retry(worksheet.update, f'Q{empty_row}', [['➕']])
    if result:
        logger.info("Успешно установили флаг '5% алерт'.")
    return result
