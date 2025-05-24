# logger.py
import sys

from loguru import logger

logger.remove()

logger.add(
    sys.stderr,
    format="<level>{time:YYYY-MM-DD HH:mm:ss}</level> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level>",
    colorize=True,
)
