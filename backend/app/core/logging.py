"""Minimal structured-ish logging setup. Called once at app startup."""
from __future__ import annotations

import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    level = logging.DEBUG if settings.DEBUG else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy libraries in production.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING if settings.is_production else logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
