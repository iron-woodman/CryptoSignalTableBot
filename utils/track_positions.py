from .google_sheet import *
import datetime
import time
from .tg_signal import send_alert, send_av_alert
from .logger_setup import logger
import threading
from .get_bybit_data import websocket_bybit
from queue import Queue

# --- Управление потоками WebSocket ---
# Словарь для хранения активных потоков и очередей для каждой монеты
# Формат: {'BTCUSDT': {'thread': <Thread_object>, 'subscribers': [<Queue_object>, ...]}}
active_ws_threads = {}


def row_order_iterator(empty_row, order_number):
    """
    Создает генератор для получения следующего номера строки и номера ордера.

    Args:
        empty_row (int): Начальный номер свободной строки.
        order_number (int): Начальный номер ордера.

    Yields:
        tuple[int, int]: Следующий номер строки и номер ордера.
    """
    while True:
        empty_row += 1
        order_number += 1
        yield empty_row, order_number


def get_time():
    """
    Возвращает текущее время в двух форматах.

    Returns:
        tuple[str, str]: Время в формате "дд.мм, ЧЧ:ММ" и "дд.мм.гг".
    """
    current_datetime = datetime.datetime.utcnow()
    utc_offset = datetime.timedelta(hours=3)
    current_datetime_utc3 = current_datetime + utc_offset
    return current_datetime_utc3.strftime("%d.%m, %H:%M"), current_datetime_utc3.strftime("%d.%m.%y")


def get_avg_and_volume(side, avg_price, av_orders_perc, total_volume, average_price_data, average_volume_data):
    """
    Рассчитывает цены и объемы для усредняющих ордеров.

    Returns:
        tuple: Обновленные данные по средней цене, объемам и списки ордеров.
    """
    average_orders_list = []
    avg_prices_list = []
    average_volume_list = []
    volumes_list = []
    for i in range(5):
        if side == "LONG":
            average_order = avg_price - (avg_price * av_orders_perc[i])
        else: # SHORT
            average_order = avg_price + (avg_price * av_orders_perc[i])
        volume = total_volume * 1.5
        average_price_data += average_order * volume
        average_volume_data += volume
        avg_price = average_price_data / average_volume_data
        total_volume += volume
        average_orders_list.append(round(average_order, 8))
        avg_prices_list.append(round(avg_price, 8))
        average_volume_list.append(round(volume, 8))
        volumes_list.append(round(total_volume, 8))
    return average_price_data, average_volume_data, average_orders_list, \
        avg_prices_list, average_volume_list, volumes_list


def change_volume(total_volume):
    """
    Пересчитывает объемы после частичного закрытия позиции (взятия TP).
    """
    average_volume_list = []
    volumes_list = []
    for i in range(5):
        volume = total_volume * 1.5
        total_volume += volume
        average_volume_list.append(volume)
        volumes_list.append(total_volume)
    return average_volume_list, volumes_list


def get_breakeven(side, price):
    """
    Рассчитывает цену безубытка с учетом комиссии.

    Args:
        side (str): Направление сделки ('LONG' или 'SHORT').
        price (float): Цена входа.

    Returns:
        float: Цена безубытка.
    """
    fee = 0.0008  # Примерная комиссия
    if side == "LONG":
        breakeven = price * (1 + fee)
    else: # SHORT
        breakeven = price * (1 - fee)
    return round(breakeven, 8)


def manage_websocket_connection(coin):
    """
    Проверяет и управляет WebSocket-соединением для указанной монеты.
    Запускает новый поток, только если для этой монеты нет активного.
    Создает отдельную очередь для каждого вызывающего (подписчика).

    Args:
        coin (str): Название монеты.

    Returns:
        Queue: Очередь для получения цен от WebSocket.
    """
    # Создаем новую очередь для текущего подписчика
    new_queue = Queue()

    # Проверяем, есть ли уже поток для этой монеты и жив ли он
    if coin in active_ws_threads and active_ws_threads[coin]['thread'].is_alive():
        logger.debug(f"Используется существующий WebSocket-поток для {coin}.")
        active_ws_threads[coin]['subscribers'].append(new_queue)
        return new_queue

    # Если потока нет или он "мертв", создаем новый
    logger.info(f"Создание нового WebSocket-потока для {coin}.")
    subscribers = [new_queue]
    ws_thread = threading.Thread(target=websocket_bybit, args=(coin, subscribers), daemon=True)
    ws_thread.start()

    # Сохраняем новый поток и список подписчиков
    active_ws_threads[coin] = {'thread': ws_thread, 'subscribers': subscribers}
    return new_queue


def track_position(worksheet, is_old_order, signal, empty_row=None, order_number=None):
    """
    Основная функция отслеживания позиции. Запускается в отдельном потоке для каждой сделки.
    Обрабатывает как новые сигналы, так и незавершенные сделки из таблицы.

    Args:
        worksheet (gspread.Worksheet): Объект рабочего листа Google.
        is_old_order (bool): True, если сделка загружена из таблицы, False - если это новый сигнал.
        signal (dict or list): Данные по сделке.
        empty_row (int, optional): Номер строки для новой сделки.
        order_number (int, optional): Номер для новой сделки.
    """
    # --- Инициализация переменных для сделки ---
    full_date_time_opened = None
    entry_price = 0.0
    coin = ''
    side = ''
    targets = []
    id_targets = []
    current_price = None
    tp_count = 0
    is_order_exist = False
    is_5_perc_alert = False

    # --- Переменные для усреднений ---
    entry_volume = 1000
    total_volume = entry_volume
    breakeven = 0.0
    avg_price = 0.0
    average_orders_list = []
    id_average_orders = []
    avg_prices_list = []
    volumes_list = []
    average_volume_list = []
    av_orders_perc = [0.1, 0.2, 0.2, 0.4, 0.8]
    was_3_averaging = False
    queue_bybit = None

    ECOSYSTEM_LINK: str = "🐋 Ecosystem x10: @valcapital"
    # --- Обработка нового сигнала ---
    if not is_old_order:
        try:
            logger.info(f'Новый сигнал из ТГ: {signal}')
            coin = signal['coin'].replace("/", "")
            side = signal['side']
            targets = [signal[f'tp{i}'] for i in range(1, 6)]
            id_targets = targets.copy()

            # Запуск WebSocket для получения цены
            queue_bybit = manage_websocket_connection(coin)
            while current_price is None or current_price == 0.0:
                time.sleep(1)
                if not queue_bybit.empty():
                    current_price = float(queue_bybit.get())

            entry_price = current_price
            avg_price = current_price

            # Расчет усреднений
            average_price_data = avg_price * entry_volume
            average_volume_data = entry_volume
            _, _, average_orders_list, avg_prices_list, \
                average_volume_list, volumes_list = get_avg_and_volume(side, avg_price, av_orders_perc, total_volume,
                                                                       average_price_data, average_volume_data)
            id_average_orders = average_orders_list.copy()
            full_date_time_opened, _ = get_time()
            breakeven = get_breakeven(side, current_price)
            is_order_exist = True

            # Запись в Google таблицу
            gs_first_update(worksheet, coin, side, full_date_time_opened, current_price, *targets,
                            is_order_exist, empty_row, order_number)

        except Exception as e:
            logger.exception(f'Ошибка в track_position() при обработке нового ордера: {e}')

    # --- Обработка существующей сделки из таблицы ---
    if is_old_order:
        try:
            logger.info(f'Загрузка ордера из таблицы: {signal}')
            empty_row = int(signal[0]) + 1
            coin = signal[1]
            side = signal[2]
            full_date_time_opened = signal[3]
            entry_price = float(signal[4].replace(",", "."))
            targets = [float(signal[i].replace(",", ".")) for i in range(5, 10)]
            id_targets = targets.copy()
            average_orders_number = int(signal[10])
            tp_count = int(signal[14])
            is_5_perc_alert = (signal[16] == '➕')

            # Запуск WebSocket
            queue_bybit = manage_websocket_connection(coin)
            while current_price is None or current_price == 0.0:
                time.sleep(1)
                if not queue_bybit.empty():
                    current_price = float(queue_bybit.get())

            # Пересчет состояния сделки с учетом уже произошедших событий (TP, усреднения)
            average_price_data = entry_price * entry_volume
            average_volume_data = entry_volume
            _, _, average_orders_list, avg_prices_list, \
                average_volume_list, volumes_list = get_avg_and_volume(side, entry_price, av_orders_perc,
                                                                       total_volume, average_price_data,
                                                                       average_volume_data)
            id_average_orders = average_orders_list.copy()
            id_avg_prices_list = avg_prices_list.copy()

            # Корректировка в зависимости от количества взятых TP и усреднений
            if tp_count > 0:
                for _ in range(tp_count):
                    targets.pop(0)
                    total_volume -= (entry_volume * 0.2)
            if average_orders_number > 0:
                for _ in range(average_orders_number):
                    average_orders_list.pop(0)
                    avg_prices_list.pop(0)
                    average_volume_list.pop(0)
                    volumes_list.pop(0)

            average_volume_list, volumes_list = change_volume(total_volume)
            last_avg_price = id_avg_prices_list[average_orders_number - 1] if average_orders_number > 0 else entry_price
            breakeven = get_breakeven(side, last_avg_price)

            is_order_exist = True

        except Exception as e:
            logger.exception(f'Ошибка в track_position() при обработке старого ордера: {e}')

    # --- Основной цикл отслеживания ---
    while is_order_exist:
        time.sleep(0.3)
        try:
            # Получение актуальной цены
            if not queue_bybit.empty():
                current_price = float(queue_bybit.get())
            if current_price is None or current_price == 0:
                continue

            # Проверка отклонения на 5% для алерта
            if not is_5_perc_alert:
                price_change = (current_price - entry_price) / entry_price
                if (side == 'LONG' and price_change < -0.05) or (side == 'SHORT' and price_change > 0.05):
                    # tg_msg = f"[{side}]: {coin} (⏰ {full_date_time_opened} msk).\n" \
                    #          f"Цена отклонилась на -5%, желательно запросить усреднение."
                    tg_msg = f"💰 <b>#{coin.replace('USDT','/USDT')} [{side}]</b>\n⏰ {full_date_time_opened} msk\n\n" \
                             f"❗️ Цена отклонилась на -5%, желательно запросить усреднение.\n" \
                             f"❗ До усреднения не забудьте отменить первоначальный стоп-лосс.\n\n{ECOSYSTEM_LINK}"

                    send_alert(tg_msg)
                    logger.info(tg_msg)
                    is_5_perc_alert = True
                    gs_5_perc_alert_update(worksheet, empty_row)

            # Проверка тейк-профитов (только если не было 3-х усреднений)
            if not was_3_averaging:
                for target_price in targets:
                    if (side == "LONG" and current_price >= target_price) or \
                       (side == "SHORT" and current_price <= target_price):

                        tp_id = id_targets.index(target_price) + 1
                        # tg_msg = f"✅ Взяли {tp_id} цель 🔥\n[{side}]: {coin} (⏰ {full_date_time_opened} msk).\n" \
                        #          f"Цена: {target_price}"

                        tg_msg = (f"✅ Взяли {tp_id} цель 🔥\n💰 <b>#{coin.replace('USDT','/USDT')} [{side}]</b>"
                                  f"(⏰ {full_date_time_opened} msk).\n"
                                  f"Цена: {target_price}\n"
                                  f"{ECOSYSTEM_LINK}")

                        send_alert(tg_msg)
                        logger.info(f'{tg_msg}\nТекущая цена: {current_price}')

                        # Если это последний TP - закрываем сделку
                        if len(targets) == 1:
                            is_order_exist = False
                            gs_final_tp_update(worksheet, tp_id, empty_row, is_order_exist)
                        else: # Иначе обновляем данные
                            targets.remove(target_price)
                            gs_tp_update(worksheet, tp_id, empty_row)
                            total_volume -= (entry_volume * 0.2)
                            average_volume_list, volumes_list = change_volume(total_volume)
                        break

            # Проверка безубытка (только после 3-го усреднения)
            if was_3_averaging:
                if (side == "LONG" and current_price >= breakeven) or \
                   (side == "SHORT" and current_price <= breakeven):
                    tg_msg = f"✅ Достигли безубытка 🔥\n[{side}]: {coin} \n(⏰ {full_date_time_opened} msk).\n\n" \
                             f"Цена: {breakeven}"
                    send_av_alert(tg_msg)
                    logger.info(f'{tg_msg}\nТекущая цена: {current_price}')
                    is_order_exist = False
                    gs_breakeven_update(worksheet, empty_row, is_order_exist)
                    break

            # Проверка усредняющих ордеров
            for i, av_order in enumerate(average_orders_list):
                if (side == "LONG" and current_price <= av_order) or \
                   (side == "SHORT" and current_price >= av_order):
                    id_av = id_average_orders.index(av_order) + 1
                    breakeven = get_breakeven(side, avg_prices_list[i])
                    total_volume += average_volume_list[i]
                    tg_msg = f"✔️ Усреднили позицию - {id_av} ордер\n[{side}]: {coin} " \
                             f"(⏰ {full_date_time_opened} msk).\n" \
                             f"Цена: {av_order}\n" \
                             f"Средняя цена входа: {avg_prices_list[i]}\n" \
                             f"Цена безубытка: {breakeven}"
                    send_av_alert(tg_msg)
                    logger.info(f'{tg_msg}\nТекущая цена: {current_price}')

                    average_orders_list.pop(i)
                    avg_prices_list.pop(i)
                    average_volume_list.pop(i)
                    volumes_list.pop(i)
                    gs_av_update(worksheet, id_av, empty_row, av_order)
                    if id_av >= 3:
                        was_3_averaging = True
                    break

        except Exception as e:
            logger.exception(f'Ошибка в track_position() в цикле while: {e}')

    # Очистка очереди после завершения отслеживания
    if queue_bybit and coin in active_ws_threads:
        try:
            active_ws_threads[coin]['subscribers'].remove(queue_bybit)
            logger.debug(f"Очередь для {coin} удалена из подписчиков.")
        except ValueError:
            pass
