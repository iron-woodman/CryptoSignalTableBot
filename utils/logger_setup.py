from loguru import logger
from config import LOG_PONG_MESSAGES

# Определяем уровень логирования для файла в зависимости от настройки LOG_PONG_MESSAGES
file_log_level = "DEBUG" if LOG_PONG_MESSAGES else "INFO"

logger.configure(
    handlers=[
        {
            "sink": "bot.log",
            "format": "{time:YY-MM-DD HH:mm:ss} | {level} | {message}",
            "level": file_log_level,
            "rotation": "2 MB",
            "retention": "30 days"
        }
    ]
)
