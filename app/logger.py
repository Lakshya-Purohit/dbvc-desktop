"""
Centralized logging with rotating file handler + Qt signal handler.

Usage:
    from app.logger import get_logger, qt_log_handler
    log = get_logger("introspection")
    log.info("Fetched 42 tables")

    # Connect the Qt handler to a UI log panel:
    qt_log_handler.log_signal.connect(my_log_panel.append_log)
"""

import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

from PyQt6.QtCore import QObject, pyqtSignal

from app.config import LOG_DIR, LOG_MAX_BYTES, LOG_BACKUP_COUNT, LOG_FORMAT, LOG_DATE_FORMAT


# ── Qt Signal Bridge ─────────────────────────────────────────────────────
class _LogSignalBridge(QObject):
    """Emits (level_name: str, formatted_message: str) on every log record."""
    log_signal = pyqtSignal(str, str)


class QtLogHandler(logging.Handler):
    """Handler that routes log records to a Qt signal for the UI."""

    def __init__(self):
        super().__init__()
        self.bridge = _LogSignalBridge()
        self.log_signal = self.bridge.log_signal

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            self.bridge.log_signal.emit(record.levelname, msg)
        except Exception:
            self.handleError(record)


# ── Module-level singletons ──────────────────────────────────────────────
_root_configured = False
qt_log_handler = QtLogHandler()


def _configure_root():
    """Set up the root logger once."""
    global _root_configured
    if _root_configured:
        return
    _root_configured = True

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    # File handler — daily-named, rotating
    today = datetime.now().strftime("%Y-%m-%d")
    file_path = os.path.join(LOG_DIR, f"dbvc_{today}.log")
    fh = RotatingFileHandler(
        file_path,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    root.addHandler(fh)

    # Console handler (for development)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    root.addHandler(ch)

    # Qt handler
    qt_log_handler.setLevel(logging.DEBUG)
    qt_log_handler.setFormatter(formatter)
    root.addHandler(qt_log_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a named child logger. Auto-configures root on first call."""
    _configure_root()
    return logging.getLogger(f"dbvc.{name}")
