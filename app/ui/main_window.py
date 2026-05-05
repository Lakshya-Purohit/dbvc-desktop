"""
Main window — sidebar navigation + stacked pages.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QStatusBar, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from app.services.snapshot_store import SnapshotStore
from app.logger import get_logger

log = get_logger("main_window")


class MainWindow(QMainWindow):
    """Application main window with sidebar navigation."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DBVC Desktop — Database Version Control")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)

        # Shared store
        self.store = SnapshotStore()

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(4)

        # Title
        title = QLabel("🧬 DBVC")
        title.setObjectName("sidebarTitle")
        sidebar_layout.addWidget(title)
        sidebar_layout.addSpacing(20)

        # Nav buttons
        self.nav_buttons = []
        nav_items = [
            ("🔌  Connections", 0),
            ("📸  Snapshots", 1),
            ("🔍  Compare", 2),
            ("📜  History", 3),
            ("⚡  Apply", 4),
            ("📋  Logs", 5),
        ]

        for label, idx in nav_items:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, i=idx: self._switch_page(i))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Version label
        version_label = QLabel("v1.0.0")
        version_label.setObjectName("sidebarVersion")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(version_label)

        credits_label = QLabel("Made with ❤️ by Lakshya Purohit")
        credits_label.setObjectName("sidebarVersion")
        credits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        credits_label.setWordWrap(True)
        sidebar_layout.addWidget(credits_label)

        main_layout.addWidget(sidebar)

        # ── Page Stack ───────────────────────────────────────────────
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # Import pages here to avoid circular imports
        from app.ui.connection_page import ConnectionPage
        from app.ui.snapshot_page import SnapshotPage
        from app.ui.compare_page import ComparePage
        from app.ui.history_page import HistoryPage
        from app.ui.apply_page import ApplyPage
        from app.ui.log_panel import LogPanel

        self.connection_page = ConnectionPage(self.store)
        self.snapshot_page = SnapshotPage(self.store)
        self.compare_page = ComparePage(self.store)
        self.history_page = HistoryPage(self.store)
        self.apply_page = ApplyPage(self.store)
        self.log_panel = LogPanel()

        self.stack.addWidget(self.connection_page)    # 0
        self.stack.addWidget(self.snapshot_page)       # 1
        self.stack.addWidget(self.compare_page)        # 2
        self.stack.addWidget(self.history_page)        # 3
        self.stack.addWidget(self.apply_page)          # 4
        self.stack.addWidget(self.log_panel)           # 5

        # ── Status Bar ───────────────────────────────────────────────
        status = QStatusBar()
        self.setStatusBar(status)
        self.status_label = QLabel("Ready")
        status.addWidget(self.status_label)

        # Default to connections page
        self._switch_page(0)

        log.info("Main window initialized")

    def _switch_page(self, index: int):
        """Switch the stacked widget to the given page index."""
        self.stack.setCurrentIndex(index)

        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        page_names = ["Connections", "Snapshots", "Compare", "History", "Apply", "Logs"]
        self.status_label.setText(f"📍 {page_names[index]}")

        # Refresh pages when switching to them
        current = self.stack.currentWidget()
        if hasattr(current, "refresh"):
            current.refresh()

        log.debug("Switched to page: %s", page_names[index])
