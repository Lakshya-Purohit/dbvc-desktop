"""
Log Panel — live scrolling log viewer.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QComboBox, QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor, QFont

from app.logger import qt_log_handler, get_logger

log = get_logger("log_panel")

LEVEL_COLORS = {
    "DEBUG": "#64748b",
    "INFO": "#e5e7eb",
    "WARNING": "#fbbf24",
    "ERROR": "#ef4444",
    "CRITICAL": "#f87171",
}


class LogPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Application Logs")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel("Real-time log output. Logs are also saved to disk.")
        subtitle.setObjectName("sectionSubtitle")
        layout.addWidget(subtitle)

        # Toolbar
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Filter:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["ALL", "DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_filter.setCurrentText("ALL")
        toolbar.addWidget(self.level_filter)

        toolbar.addStretch()

        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setProperty("cssClass", "secondary")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(clear_btn)

        export_btn = QPushButton("💾 Export")
        export_btn.setProperty("cssClass", "secondary")
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self._export)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        # Log display
        self.log_display = QPlainTextEdit()
        self.log_display.setObjectName("logPanel")
        self.log_display.setReadOnly(True)
        self.log_display.setFont(QFont("Cascadia Code", 11))
        self.log_display.setMaximumBlockCount(5000)
        layout.addWidget(self.log_display)

        # Status
        self.count_label = QLabel("0 log entries")
        self.count_label.setObjectName("sectionSubtitle")
        layout.addWidget(self.count_label)

        # Connect to Qt log handler
        qt_log_handler.log_signal.connect(self._append_log)
        self._log_count = 0

    def _append_log(self, level: str, message: str):
        """Append a log entry to the display."""
        # Check filter
        current_filter = self.level_filter.currentText()
        if current_filter != "ALL":
            levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if levels.index(level) < levels.index(current_filter):
                return

        cursor = self.log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        color = LEVEL_COLORS.get(level, "#e5e7eb")
        fmt.setForeground(QColor(color))

        cursor.insertText(message + "\n", fmt)

        # Auto-scroll to bottom
        self.log_display.setTextCursor(cursor)
        self.log_display.ensureCursorVisible()

        self._log_count += 1
        self.count_label.setText(f"{self._log_count} log entries")

    def _clear(self):
        self.log_display.clear()
        self._log_count = 0
        self.count_label.setText("0 log entries")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", "dbvc_logs.txt", "Text Files (*.txt)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.log_display.toPlainText())
            log.info("Logs exported to: %s", path)

    def refresh(self):
        pass  # Logs are live, no refresh needed
