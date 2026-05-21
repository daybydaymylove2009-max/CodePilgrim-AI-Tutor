import sys
from loguru import logger

logger.remove()

logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <yellow>{extra[correlation_id]}</yellow> | <level>{message}</level>",
    level="INFO",
)

logger.add(
    "logs/codepilgrim_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {extra[correlation_id]} | {message}",
    rotation="00:00",
    retention="30 days",
    compression="gz",
    level="DEBUG",
    serialize=True,
)

logger.configure(extra={"correlation_id": "-"})
