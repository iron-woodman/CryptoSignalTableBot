from .logger_setup import logger


def parse_signal_data2(new_signal: str) -> dict | None:
    """
    Разбирает текстовый сигнал нового формата и преобразует его в словарь.

    Args:
        new_signal (str): Текст сигнала из Telegram.

    Returns:
        dict | None: Словарь с данными сигнала (монета, направление, TP, SL) или None в случае ошибки.
    """
    try:
        signal_dict = {}
        lines = [line.strip() for line in new_signal.split('\n') if line.strip()]

        # --- Извлечение монеты и направления ---
        first_line = lines[0]
        if "LONG:" in first_line:
            signal_dict['side'] = 'LONG'
            signal_dict['coin'] = first_line.split("LONG:")[1].strip()
        elif "SHORT:" in first_line:
            signal_dict['side'] = 'SHORT'
            signal_dict['coin'] = first_line.split("SHORT:")[1].strip()
        else:
            logger.error(f'Не удалось определить LONG/SHORT в сигнале:\n{new_signal}')
            return None

        # --- Извлечение стоп-лосса ---
        stop_line = next((line for line in lines if 'Стоп:' in line), None)
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
            if 'Цели:' in line:
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
            price_str = line.split(')')[1].split('(')[0].strip().rstrip('.')
            signal_dict[f'tp{i + 1}'] = float(price_str)

        return signal_dict

    except (IndexError, ValueError) as e:
        logger.error(f'Ошибка при парсинге сигнала:\n{new_signal}\nОшибка: {e}')
        return None
    except Exception as e:
        logger.error(f'Непредвиденная ошибка в parse_signal_data2(): {e}')
        return None
