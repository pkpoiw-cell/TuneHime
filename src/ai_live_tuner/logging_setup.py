from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .settings import log_dir


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("ai_live_tuner")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        log_dir() / "app.log",
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger
