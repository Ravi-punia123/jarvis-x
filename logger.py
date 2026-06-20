"""Central logging utilities for JARVIS."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


_LOGGER: Optional[logging.Logger] = None


def get_logger(name: str = "jarvis") -> logging.Logger:
    global _LOGGER
    if _LOGGER is None:
        log_dir = Path.cwd() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "jarvis.log"

        logger = logging.getLogger("jarvis")
        logger.setLevel(logging.INFO)
        logger.handlers = []

        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

        # Rotating file handler (10MB max per file, keeping up to 5 files)
        fh = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        logger.addHandler(sh)

        _LOGGER = logger

    return _LOGGER.getChild(name) if name != "jarvis" else _LOGGER
