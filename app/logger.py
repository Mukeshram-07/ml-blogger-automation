"""
logger.py
---------
Centralized logging setup using Python's standard logging module.
Writes to both console and a rotating log file.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import config


def get_logger(name: str = "ml_blogger") -> logging.Logger:
    """
    Returns a configured logger instance.
    - Console output: INFO level
    - File output: DEBUG level with rotation (5 MB max, 3 backups)
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured — return existing logger
        return logger

    logger.setLevel(logging.DEBUG)

    # ── Formatter ─────────────────────────────────────────────────────────
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── Console handler ───────────────────────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)

    # ── File handler ──────────────────────────────────────────────────────
    os.makedirs(config.LOG_DIR, exist_ok=True)
    file_handler = RotatingFileHandler(
        filename=config.LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = get_logger()
