from .logger_setup import logger
from typing import Union


def parse_signal_data2(new_signal: str) -> Union[dict, None]:
    """
    Разбирает текстовый сигнал нового формата и преобразует его в словарь.

    Args:
        new_signal (str): Текст сигнала из Telegram.

    Returns:
        Union[dict, None]: Словарь с данными сигнала (монета, направление, TP, SL, exchange) или None в случае ошибки.
    """
    try:
        signal_dict = {}
        lines = [line.strip() for line in new_signal.split('\n') if line.strip()]

        # --- Определение биржи ---
        # Проверяем наличие упоминания биржи в сигнале
        signal_text_lower = new_signal.lower()
        if 'bingx' in signal_text_lower:
            signal_dict['exchange'] = 'bingx'
        elif 'bybit' in signal_text_lower:
            signal_dict['exchange'] = 'bybit'
        else:
            # Если биржа не указана, по умолчанию используем bybit
            signal_dict['exchange'] = 'bybit'

        # --- Извлечение монеты и направления ---
        first_line = lines[0]
        if "LONG" in first_line:
            signal_dict['side'] = 'LONG'
            signal_dict['coin'] = first_line.split("[LONG]")[0].strip().replace('🚀 #','')
        elif "SHORT" in first_line:
            signal_dict['side'] = 'SHORT'
            signal_dict['coin'] = first_line.split("[SHORT]")[0].strip().replace('🚀 #','')
        else:
            logger.error(f'Не удалось определить LONG/SHORT в сигнале:\n{new_signal}')
            return None

        # --- Извлечение стоп-лосса ---
        stop_line = next((line for line in lines if 'Stop-loss:' in line), None)
        if stop_line:
            stop_loss_str = stop_line.split(':')[1].strip()
            signal_dict['sl'] = float(stop_loss_str)
        else:
            logger.error(f'Не удалось найти стоп-лосс в сигнале:\n{new_signal}')
            return None

        # --- Извлечение тейк-профитов ---
        tp_lines = []
        is_tp_section = False
        for line in lines:
            if 'Take-Profit:' in line:
                is_tp_section = True
                continue
            if is_tp_section:
                # Проверяем, что строка начинается с цифры и скобки, например, "1)"
                if line and line[0].isdigit() and ')' in line:
                    tp_lines.append(line)
                else:
                    # Если дошли до строки, не являющейся целью, заканчиваем сбор
                    break
        
        if not tp_lines:
            logger.error(f'Не удалось найти цели (TP) в сигнале:\n{new_signal}')
            return None
            
        for i, line in enumerate(tp_lines):
            # Извлекаем цену, убирая лишние символы
            price_str = line.split(')')[1].split('(')[0].strip().rstrip('.').replace(',', '.')
            signal_dict[f'tp{i + 1}'] = float(price_str)

        return signal_dict

    except (IndexError, ValueError) as e:
        logger.error(f'Ошибка при парсинге сигнала:\n{new_signal}\nОшибка: {e}')
        return None
    except Exception as e:
        logger.error(f'Непредвиденная ошибка в parse_signal_data2(): {e}')
        return None
