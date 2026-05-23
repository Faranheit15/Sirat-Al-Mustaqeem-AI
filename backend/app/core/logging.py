"""Centralised logging configuration for the Sirat Al Mustaqeem AI backend.

Call ``setup_logging`` once at application startup (inside ``create_app``).
Every other module should obtain its logger via ``get_logger(__name__)``.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# JSON formatter — used in production so container log drivers (CloudWatch,
# Datadog, GCP Logging …) can parse structured fields automatically.
# ---------------------------------------------------------------------------

_LOG_RECORD_BUILTIN_ATTRS = frozenset(
    {
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info and record.exc_info[1] is not None:
            log_data["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)

        # Forward any *extra* key-value pairs the caller attached.
        for key, value in record.__dict__.items():
            if key not in _LOG_RECORD_BUILTIN_ATTRS and key not in log_data:
                log_data[key] = value

        return json.dumps(log_data, default=str)


# ---------------------------------------------------------------------------
# Human-readable formatter — used in local / development environments.
# ---------------------------------------------------------------------------

_DEV_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DEV_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_LOCAL_ENVIRONMENTS = frozenset({"local", "dev", "development", "test"})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def setup_logging(log_level: str, environment: str) -> None:
    """Configure the root ``app`` logger and suppress noisy third-party loggers.

    Must be called **once** at application startup before any log statements
    are emitted.

    Parameters
    ----------
    log_level:
        One of ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.
    environment:
        The deployment environment (e.g. ``development``, ``production``).
        Controls whether output is human-readable or structured JSON.
    """
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    is_local = environment.lower() in _LOCAL_ENVIRONMENTS
    handler = logging.StreamHandler(sys.stdout)

    if is_local:
        handler.setFormatter(logging.Formatter(fmt=_DEV_FORMAT, datefmt=_DEV_DATE_FORMAT))
    else:
        handler.setFormatter(JSONFormatter())

    # Configure the ``app`` namespace logger so every ``app.*`` child inherits.
    app_logger = logging.getLogger("app")
    app_logger.setLevel(numeric_level)
    app_logger.handlers.clear()
    app_logger.addHandler(handler)
    app_logger.propagate = False

    # Suppress noisy third-party loggers.
    for noisy in ("uvicorn.access", "httpx", "httpcore", "openai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the ``app`` namespace.

    Usage::

        from app.core.logging import get_logger
        logger = get_logger(__name__)
    """
    prefix = "app."
    qualified = name if name.startswith(prefix) else f"{prefix}{name}"
    return logging.getLogger(qualified)
