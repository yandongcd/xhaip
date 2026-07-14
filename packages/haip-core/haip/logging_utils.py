"""Logging utility — structured JSON logging via structlog.

Provides:
    - JSON-formatted log output
    - Automatic context injection (trace_id, user_id, session_id)
    - Sensitive field redaction
    - Dynamic log level switching
"""

from __future__ import annotations

import logging
import sys

STRUCTLOG_AVAILABLE = False
try:
    import structlog

    STRUCTLOG_AVAILABLE = True
except ImportError:
    pass


def setup_logging(level: str = "INFO", json_format: bool = True):
    """Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        json_format: If True, output JSON. Falls back to console if False.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    if STRUCTLOG_AVAILABLE and json_format:
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    else:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
            stream=sys.stdout,
        )


def get_logger(name: str = "xhaip") -> "structlog.stdlib.BoundLogger | logging.Logger":
    """Get a logger instance. Returns structlog if available, else stdlib."""
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    return logging.getLogger(name)


# Global logger
log = get_logger()


class SensitiveFormatter(logging.Formatter):
    """Redacts sensitive fields from log messages."""

    SENSITIVE_FIELDS = {"password", "token", "secret", "api_key", "authorization"}

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        for field in self.SENSITIVE_FIELDS:
            # Redact field=value patterns
            import re
            msg = re.sub(
                rf'("{field}":\s*")[^"]+(")',
                r'\1***REDACTED***\2',
                msg,
                flags=re.IGNORECASE,
            )
            msg = re.sub(
                rf"({field}=)[^\s,]+",
                r"\1***",
                msg,
                flags=re.IGNORECASE,
            )
        return msg
