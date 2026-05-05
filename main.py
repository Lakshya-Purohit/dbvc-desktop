"""
DBVC Desktop — Database Version Control for Windows
Entry point.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from app.ui.styles import apply_theme
from app.ui.main_window import MainWindow
from app.logger import get_logger

log = get_logger("main")


def main():
    log.info("=" * 60)
    log.info("DBVC Desktop starting...")
    log.info("=" * 60)

    app = QApplication(sys.argv)
    app.setApplicationName("DBVC Desktop")
    app.setApplicationVersion("1.0.0")

    # Apply dark theme
    apply_theme(app)

    # Create and show main window
    window = MainWindow()
    window.show()

    log.info("Application window opened")

    exit_code = app.exec()

    log.info("Application closed (exit code: %d)", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
