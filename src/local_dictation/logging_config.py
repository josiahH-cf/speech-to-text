from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import logs_dir

LOGGER_NAME = "local_dictation"


def configure_logging(settings: dict, *, console: bool = False) -> logging.Logger:
    log_settings = settings.get("logging", {})
    level_name = str(log_settings.get("level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    keep_files = int(log_settings.get("keep_files", 5))

    target_dir = logs_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    log_path = target_dir / "local-dictation.log"

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=max(1, keep_files),
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    if name:
        return logging.getLogger(f"{LOGGER_NAME}.{name}")
    return logging.getLogger(LOGGER_NAME)


def log_file_path() -> Path:
    return logs_dir() / "local-dictation.log"
