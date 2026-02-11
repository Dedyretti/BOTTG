import logging
import sys
from typing import Optional


def setup_logging(
    name: str = "attendance_bot",
    level: str = "INFO",
    format_string: Optional[str] = None,
) -> logging.Logger:
    """Настраивает логгер с заданным именем, уровнем и форматом."""

    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    log_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        formatter = logging.Formatter(format_string)
        console_handler.setFormatter(formatter)

        logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "attendance_bot") -> logging.Logger:
    return logging.getLogger(name)
