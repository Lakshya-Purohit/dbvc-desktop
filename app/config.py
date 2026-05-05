"""
Application configuration — paths, constants, auto-created directories.
"""

import os
import sys

APP_NAME = "DBVC"
APP_VERSION = "1.0.0"

# ── Data directory (%APPDATA%/DBVC) ──────────────────────────────────────
if sys.platform == "win32":
    _base = os.environ.get("APPDATA", os.path.expanduser("~"))
else:
    _base = os.path.expanduser("~/.local/share")

DATA_DIR = os.path.join(_base, APP_NAME)
LOG_DIR = os.path.join(DATA_DIR, "logs")
DB_PATH = os.path.join(DATA_DIR, "dbvc.sqlite")

# ── Logging ──────────────────────────────────────────────────────────────
LOG_MAX_BYTES = 10 * 1024 * 1024   # 10 MB per file
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "[%(asctime)s] [%(levelname)-7s] [%(name)-18s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── Ensure directories exist on import ───────────────────────────────────
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
