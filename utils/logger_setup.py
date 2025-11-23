from loguru import logger

logger.configure(
    handlers=[
        {
            "sink": "bot.log",
            "format": "{time:YY-MM-DD HH:mm:ss} | {level} | {message}",
            "level": "DEBUG",
            "rotation": "2 MB",
            "retention": "30 days"
        }
    ]
)
