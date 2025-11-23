import time
import gspread
from .logger_setup import logger
from config import GS_JS_FILE, GS_SHEET_FILE, G_LIST
from .tg_signal import send_tech_alert

# --- Глобальные переменные ---
js_file = GS_JS_FILE  # Имя файла с ключом Google API
sheet_url = GS_SHEET_FILE  # URL Google таблицы
google_status = False  # Статус подключения к Google API
is_checked = False  # Флаг для отслеживания первой проверки подключения
list_number = int(G_LIST)  # Номер листа в таблице


def exception_def(google_status, is_checked):
    """
    Обрабатывает исключения при работе с Google API.
    Отправляет уведомление об ошибке и делает паузу.

    Args:
        google_status (bool): Текущий статус подключения.
        is_checked (bool): Флаг, была ли уже проверка.

    Returns:
        tuple[bool, bool]: Обновленные google_status и is_checked.
    """
    if google_status:
        google_status = send_tech_g_alert(google_status)
    if not is_checked:
        is_checked, google_status = True, True
        google_status = send_tech_g_alert(google_status)
    time.sleep(5)
    return google_status, is_checked


def send_tech_g_alert(google_status):
    """
    Отправляет техническое уведомление о статусе подключения к Google API.

    Args:
        google_status (bool): Текущий статус подключения.

    Returns:
        bool: Новый статус подключения.
    """
    if not google_status:
        send_tech_alert('Подключились к Google API ✅')
        return True
    else:
        send_tech_alert('Ошибка запроса к Google API ❌')
        return False


def is_order(value):
    """
    Преобразует булево значение в символ для отображения в таблице.

    Args:
        value (bool): Значение, которое нужно преобразовать.

    Returns:
        str: '➕' если True, '➖' если False.
    """
    if value:
        return '➕'
    return '➖'


def get_empty_row(worksheet):
    """
    Находит номер первой свободной строки в таблице.

    Args:
        worksheet (gspread.Worksheet): Рабочий лист Google таблицы.

    Returns:
        int: Номер первой свободной строки.
    """
    global google_status, is_checked
    for i in range(30):
        try:
            data = worksheet.get_all_values()
            return len(data) + 1
        except gspread.exceptions.APIError:
            logger.exception(f'Ошибка подключения к Google API, переподключаюсь. Попытка номер: {i + 1}')
            google_status, is_checked = exception_def(google_status, is_checked)
        except Exception as e:
            logger.exception(f'Ошибка в get_empty_row(), {e}')
            google_status, is_checked = exception_def(google_status, is_checked)


def get_order_number(worksheet, empty_row):
    """
    Определяет порядковый номер для новой сделки.

    Args:
        worksheet (gspread.Worksheet): Рабочий лист Google таблицы.
        empty_row (int): Номер текущей свободной строки.

    Returns:
        int: Номер для новой сделки.
    """
    global google_status, is_checked
    for i in range(30):
        try:
            number = worksheet.acell(f'A{empty_row - 1}').value
            if number is None or not number.isdigit():
                return 1
            else:
                return int(number) + 1
        except gspread.exceptions.APIError:
            logger.exception(f'Ошибка подключения к Google API, переподключаюсь. Попытка номер: {i + 1}')
            google_status, is_checked = exception_def(google_status, is_checked)
        except Exception as e:
            logger.exception(f'Ошибка в get_order_number(), {e}')
            google_status, is_checked = exception_def(google_status, is_checked)


def get_old_orders():
    """
    Получает из таблицы все незавершенные сделки.

    Returns:
        tuple[list | bool, gspread.Worksheet]: Список незавершенных сделок или False, и рабочий лист.
    """
    global google_status, is_checked
    for i in range(30):
        try:
            live_trades = []
            gc = gspread.service_account(filename=js_file)
            sh = gc.open_by_url(sheet_url)
            worksheet = sh.get_worksheet(list_number)
            sheet_data = worksheet.get_all_values()
            if not google_status:
                send_tech_g_alert(google_status)
            for line in sheet_data:
                if line[12] == '➕':
                    live_trades.append(line)
            return (live_trades, worksheet) if live_trades else (False, worksheet)
        except gspread.exceptions.APIError:
            logger.exception(f'Ошибка подключения к Google API, переподключаюсь. Попытка номер: {i + 1}')
            google_status, is_checked = exception_def(google_status, is_checked)
        except Exception as e:
            logger.exception(f'Ошибка в get_old_orders(), {e}')
            google_status, is_checked = exception_def(google_status, is_checked)


def gs_first_update(coin, side, date_time, current_price, tp1, tp2, tp3, tp4, tp5, is_order_exist,
                    empty_row, order_number):
    """
    Записывает в таблицу информацию о новой сделке.
    """
    global google_status, is_checked
    for i in range(30):
        try:
            gc = gspread.service_account(filename=js_file)
            sh = gc.open_by_url(sheet_url)
            gs_coin = coin.replace('/USDT', '')
            worksheet = sh.get_worksheet(list_number)
            worksheet.update(f'A{empty_row}:Q{empty_row}', [
                [order_number, gs_coin, side, date_time, current_price, tp1, tp2, tp3, tp4, tp5, '0', '',
                 is_order(is_order_exist), '', '0', '', '➖']])
            logger.info('Обновил таблицу')
            if not google_status:
                send_tech_g_alert(google_status)
            break
        except gspread.exceptions.APIError:
            logger.exception(f'Ошибка подключения к Google API, переподключаюсь. Попытка номер: {i + 1}')
            google_status, is_checked = exception_def(google_status, is_checked)
        except Exception as e:
            logger.exception(f'Ошибка в gs_first_update, {e}')
            google_status, is_checked = exception_def(google_status, is_checked)


def gs_tp_update(tp_count, empty_row):
    """
    Обновляет в таблице количество взятых тейк-профитов.
    """
    global google_status, is_checked
    for i in range(30):
        try:
            gc = gspread.service_account(filename=js_file)
            sh = gc.open_by_url(sheet_url)
            worksheet = sh.get_worksheet(list_number)
            tp_in_gs = int(worksheet.acell(f'O{empty_row}').value)
            if tp_count > tp_in_gs:
                worksheet.update(f'O{empty_row}', [[tp_count]])
            logger.info('Обновил кол-во TP в таблице')
            if not google_status:
                send_tech_g_alert(google_status)
            return empty_row
        except gspread.exceptions.APIError:
            logger.exception(f'Ошибка подключения к Google API, переподключаюсь. Попытка номер: {i + 1}')
            google_status, is_checked = exception_def(google_status, is_checked)
        except Exception as e:
            logger.exception(f'Ошибка в gs_tp_update, {e}')
            google_status, is_checked = exception_def(google_status, is_checked)


def gs_final_tp_update(tp_count, empty_row, is_order_exist):
    """
    Обновляет количество TP и закрывает сделку в таблице.
    """
    global google_status, is_checked
    for i in range(30):
        try:
            gc = gspread.service_account(filename=js_file)
            sh = gc.open_by_url(sheet_url)
            worksheet = sh.get_worksheet(list_number)
            tp_in_gs = int(worksheet.acell(f'O{empty_row}').value)
            if tp_count > tp_in_gs:
                worksheet.update(f'O{empty_row}', [[tp_count]])
            worksheet.update(f'M{empty_row}', [[is_order(is_order_exist)]])
            logger.info('Обновил кол-во TP в таблице и статус сделки')
            if not google_status:
                send_tech_g_alert(google_status)
            break
        except gspread.exceptions.APIError:
            logger.exception(f'Ошибка подключения к Google API, переподключаюсь. Попытка номер: {i + 1}')
            google_status, is_checked = exception_def(google_status, is_checked)
        except Exception as e:
            logger.exception(f'Ошибка в gs_final_tp_update, {e}')
            google_status, is_checked = exception_def(google_status, is_checked)


def gs_stop_update(stop_loss, empty_row, is_order_exist):
    """
    Обновляет статус сделки на 'закрыто по стопу' и записывает цену стоп-лосса.
    """
    global google_status, is_checked
    for i in range(30):
        try:
            gc = gspread.service_account(filename=js_file)
            sh = gc.open_by_url(sheet_url)
            worksheet = sh.get_worksheet(list_number)
            worksheet.update(f'M{empty_row}', [[is_order(is_order_exist)]])
            worksheet.update(f'P{empty_row}', [[stop_loss]])
            logger.info('Обновил статус сделки и добавил SL')
            if not google_status:
                send_tech_g_alert(google_status)
            break
        except gspread.exceptions.APIError:
            logger.exception(f'Ошибка подключения к Google API, переподключаюсь. Попытка номер: {i + 1}')
            google_status, is_checked = exception_def(google_status, is_checked)
        except Exception as e:
            logger.exception(f'Ошибка в gs_stop_update, {e}')
            google_status, is_checked = exception_def(google_status, is_checked)


def gs_av_update(av_count, empty_row, av_order):
    """
    Обновляет в таблице количество усреднений и цену последнего усреднения.
    """
    global google_status, is_checked
    for i in range(30):
        try:
            gc = gspread.service_account(filename=js_file)
            sh = gc.open_by_url(sheet_url)
            worksheet = sh.get_worksheet(list_number)
            av_in_gs = int(worksheet.acell(f'K{empty_row}').value)
            if av_count > av_in_gs:
                worksheet.update(f'K{empty_row}', [[av_count]])
            worksheet.update(f'L{empty_row}', [[av_order]])
            logger.info('Обновил номер и цену усредняющего ордера в таблице')
            if not google_status:
                send_tech_g_alert(google_status)
            break
        except gspread.exceptions.APIError:
            logger.exception(f'Ошибка подключения к Google API, переподключаюсь. Попытка номер: {i + 1}')
            google_status, is_checked = exception_def(google_status, is_checked)
        except Exception as e:
            logger.exception(f'Ошибка в gs_av_update, {e}')
            google_status, is_checked = exception_def(google_status, is_checked)


def gs_breakeven_update(empty_row, is_order_exist):
    """
    Обновляет статус сделки на 'закрыто по безубытку'.
    """
    global google_status, is_checked
    for i in range(30):
        try:
            gc = gspread.service_account(filename=js_file)
            sh = gc.open_by_url(sheet_url)
            worksheet = sh.get_worksheet(list_number)
            worksheet.update(f'M{empty_row}', [[is_order(is_order_exist)]])
            worksheet.update(f'N{empty_row}', [['✅']])
            logger.info('Обновил статус сделки и БУ')
            if not google_status:
                send_tech_g_alert(google_status)
            break
        except gspread.exceptions.APIError:
            logger.exception(f'Ошибка подключения к Google API, переподключаюсь. Попытка номер: {i + 1}')
            google_status, is_checked = exception_def(google_status, is_checked)
        except Exception as e:
            logger.exception(f'Ошибка в gs_breakeven_update, {e}')
            google_status, is_checked = exception_def(google_status, is_checked)


def gs_5_perc_alert_update(empty_row):
    """
    Отмечает в таблице, что было отправлено уведомление о 5% отклонении цены.
    """
    global google_status, is_checked
    for i in range(30):
        try:
            gc = gspread.service_account(filename=js_file)
            sh = gc.open_by_url(sheet_url)
            worksheet = sh.get_worksheet(list_number)
            worksheet.update(f'Q{empty_row}', [['➕']])
            logger.info('Обновил статус 5% алерта в таблице')
            if not google_status:
                send_tech_g_alert(google_status)
            return empty_row
        except gspread.exceptions.APIError:
            logger.exception(f'Ошибка подключения к Google API, переподключаюсь. Попытка номер: {i + 1}')
            google_status, is_checked = exception_def(google_status, is_checked)
        except Exception as e:
            logger.exception(f'Ошибка в gs_5_perc_alert_update, {e}')
            google_status, is_checked = exception_def(google_status, is_checked)
