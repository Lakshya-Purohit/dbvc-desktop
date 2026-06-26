"""
Main window — sidebar navigation + stacked pages + auto-update checker.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QStatusBar, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize

from app.config import APP_VERSION
from app.services.snapshot_store import SnapshotStore
from app.services.update_checker import UpdateChecker
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

        # Update banner (hidden by default, shown when update is available)
        self.update_banner = QPushButton("🚀 Update Available!")
        self.update_banner.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1e40af, stop:1 #7c3aed);
                color: #e0e7ff;
                border: 1px solid #4f46e5;
                border-radius: 8px;
                padding: 10px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #2563eb, stop:1 #8b5cf6);
            }
        """)
        self.update_banner.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_banner.setVisible(False)
        self.update_banner.clicked.connect(self._show_update_dialog)
        sidebar_layout.addWidget(self.update_banner)

        # Version label
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setObjectName("sidebarVersion")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(self.version_label)

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

        # ── Auto-Update Checker ──────────────────────────────────────
        self._pending_update = None  # (version, url, notes)
        self._update_checker = UpdateChecker()
        self._update_checker.on_update_available(self._on_update_available)
        self._update_checker.start()

        log.info("Main window initialized")

    # ── Navigation ───────────────────────────────────────────────────
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

    # ── Update Handling ──────────────────────────────────────────────
    def _on_update_available(self, version: str, url: str, notes: str):
        """Called from the update checker when a newer release exists."""
        self._pending_update = (version, url, notes)

        # Show the sidebar banner
        self.update_banner.setText(f"🚀 Update {version}")
        self.update_banner.setVisible(True)

        # Update the version label to indicate outdated
        self.version_label.setText(f"v{APP_VERSION} (outdated)")
        self.version_label.setStyleSheet("color: #fbbf24;")

        # Show the popup notification immediately
        self._show_update_dialog()

    def _show_update_dialog(self):
        """Display the update notification dialog."""
        if not self._pending_update:
            return

        version, url, notes = self._pending_update

        # Import here to avoid circular imports
        from app.ui.update_dialog import UpdateDialog

        dialog = UpdateDialog(version, url, notes, parent=self)
        dialog.exec()
