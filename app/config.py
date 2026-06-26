"""
Application configuration — paths, constants, auto-created directories.
"""

import os
import sys

APP_NAME = "DBVC"


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # For development, look at the project root
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def _get_version():
    # 1. Try to read from packaged version.txt (packaged by PyInstaller)
    try:
        version_txt_path = get_resource_path(os.path.join("app", "resources", "version.txt"))
        if os.path.exists(version_txt_path):
            with open(version_txt_path, "r", encoding="utf-8") as f:
                ver = f.read().strip()
                if ver:
                    return ver.lstrip("vV")
    except Exception:
        pass

    # 2. Try to get version from git tag
    try:
        import subprocess
        # Get the latest tag from the git repository
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            capture_output=True,
            text=True,
            check=True,
            shell=True
        )
        ver = result.stdout.strip()
        if ver:
            return ver.lstrip("vV")
    except Exception:
        pass

    # 3. Try to read from a local untracked version.txt if it exists
    try:
        local_version_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.txt")
        if os.path.exists(local_version_path):
            with open(local_version_path, "r", encoding="utf-8") as f:
                ver = f.read().strip()
                if ver:
                    return ver.lstrip("vV")
    except Exception:
        pass

    # 4. Fallback if everything else fails
    return "0.0.0-dev"


APP_VERSION = _get_version()

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

