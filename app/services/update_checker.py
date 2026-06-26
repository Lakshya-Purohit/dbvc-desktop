"""
Auto-update checker — polls GitHub Releases for new versions and
emits a Qt signal when an update is available.

Runs in a background QThread so the UI stays responsive.
"""

import re
import json
import urllib.request
import urllib.error
from packaging.version import Version, InvalidVersion

from PyQt6.QtCore import QThread, pyqtSignal, QTimer

from app.config import APP_VERSION
from app.logger import get_logger

log = get_logger("update_checker")

# ── Configuration ────────────────────────────────────────────────────────
GITHUB_OWNER = "Lakshya-Purohit"
GITHUB_REPO = "dbvc-desktop"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

CHECK_INTERVAL_MS = 30 * 60 * 1000  # 30 minutes


def _parse_version(tag: str) -> Version | None:
    """Strip leading 'v' and parse as PEP 440."""
    cleaned = tag.lstrip("vV").strip()
    try:
        return Version(cleaned)
    except InvalidVersion:
        return None


class UpdateCheckWorker(QThread):
    """Background thread that checks GitHub for a newer release."""

    # Emits (latest_version_str, release_url, release_notes)
    update_available = pyqtSignal(str, str, str)
    check_finished = pyqtSignal()  # emitted even if no update / error

    def run(self):
        try:
            log.debug("Checking for updates at %s", RELEASES_URL)
            req = urllib.request.Request(
                RELEASES_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "DBVC-Desktop-UpdateChecker",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            tag = data.get("tag_name", "")
            latest = _parse_version(tag)
            current = _parse_version(APP_VERSION)

            if latest is None or current is None:
                log.warning("Could not parse versions: current=%s, latest=%s", APP_VERSION, tag)
                self.check_finished.emit()
                return

            if latest > current:
                release_url = data.get("html_url", f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases")
                body = data.get("body", "") or ""
                # Trim release notes to first 500 chars for the popup
                notes = body[:500] + ("…" if len(body) > 500 else "")
                log.info("Update available: %s → %s", APP_VERSION, tag)
                self.update_available.emit(tag, release_url, notes)
            else:
                log.debug("App is up to date (current=%s, latest=%s)", APP_VERSION, tag)

        except urllib.error.URLError as e:
            log.debug("Update check failed (network): %s", e)
        except Exception as e:
            log.warning("Update check error: %s", e)
        finally:
            self.check_finished.emit()


class UpdateChecker:
    """
    High-level controller that runs the first check shortly after app
    launch, then repeats on a timer.

    Usage::

        checker = UpdateChecker()
        checker.update_available.connect(my_handler)
        checker.start()
    """

    def __init__(self):
        self._timer = QTimer()
        self._timer.setInterval(CHECK_INTERVAL_MS)
        self._timer.timeout.connect(self._run_check)
        self._worker: UpdateCheckWorker | None = None

        # Proxy signal so callers only interact with UpdateChecker
        self.update_available = pyqtSignal  # placeholder, overridden below

    def start(self):
        """Begin periodic checking (first check after 5 s)."""
        log.info("Update checker started (interval=%d min)", CHECK_INTERVAL_MS // 60_000)
        QTimer.singleShot(5000, self._run_check)
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _run_check(self):
        if self._worker is not None and self._worker.isRunning():
            return  # previous check still in progress
        self._worker = UpdateCheckWorker()
        self._worker.update_available.connect(self._on_update)
        self._worker.start()

    def _on_update(self, version: str, url: str, notes: str):
        """Forward to whoever connected."""
        self._latest_version = version
        self._latest_url = url
        self._latest_notes = notes
        # We store and re-emit through a callback pattern
        if hasattr(self, "_callback") and self._callback:
            self._callback(version, url, notes)

    def on_update_available(self, callback):
        """Register a callback: callback(version, url, notes)."""
        self._callback = callback
