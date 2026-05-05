"""
History Page — git-log style timeline of all snapshots.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from app.services.snapshot_store import SnapshotStore
from app.logger import get_logger

log = get_logger("history")


class HistoryPage(QWidget):
    def __init__(self, store: SnapshotStore):
        super().__init__()
        self.store = store

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Version History")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel("Browse all schema snapshots — like git log. Select two to compare.")
        subtitle.setObjectName("sectionSubtitle")
        layout.addWidget(subtitle)

        # Filter
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Connection:"))
        self.conn_filter = QComboBox()
        self.conn_filter.addItem("All", "")
        self.conn_filter.currentIndexChanged.connect(self._load_history)
        filter_row.addWidget(self.conn_filter)
        filter_row.addStretch()

        compare_btn = QPushButton("🔍 Compare Selected")
        compare_btn.setProperty("cssClass", "primary")
        compare_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        compare_btn.clicked.connect(self._compare_selected)
        filter_row.addWidget(compare_btn)

        layout.addLayout(filter_row)

        # Timeline table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["", "ID", "Connection", "Label", "Message", "Date"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 40)
        self.table.setColumnWidth(1, 90)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Apply history
        ah_title = QLabel("Recent Apply History")
        ah_title.setObjectName("sectionTitle")
        ah_title.setStyleSheet("font-size:18px; margin-top:12px;")
        layout.addWidget(ah_title)

        self.apply_table = QTableWidget()
        self.apply_table.setColumnCount(5)
        self.apply_table.setHorizontalHeaderLabels(["Type", "Name", "Status", "Error", "Applied At"])
        self.apply_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.apply_table.setAlternatingRowColors(True)
        self.apply_table.verticalHeader().setVisible(False)
        self.apply_table.setMaximumHeight(200)
        layout.addWidget(self.apply_table)

        self.refresh()

    def refresh(self):
        self._load_connections()
        self._load_history()
        self._load_apply_history()

    def _load_connections(self):
        self.conn_filter.clear()
        self.conn_filter.addItem("All", "")
        for c in self.store.get_connections():
            self.conn_filter.addItem(f"{c['name']} ({c['db_type']})", c["id"])

    def _load_history(self):
        conn_id = self.conn_filter.currentData() or None
        snapshots = self.store.get_snapshots(conn_id)
        self.table.setRowCount(len(snapshots))

        for row, s in enumerate(snapshots):
            # Commit dot
            dot = QLabel("●")
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            dot.setStyleSheet("color: #22c55e; font-size: 16px; background: transparent;")
            self.table.setCellWidget(row, 0, dot)

            self.table.setItem(row, 1, QTableWidgetItem(s["id"][:8]))
            self.table.setItem(row, 2, QTableWidgetItem(s.get("connection_name", "—")))
            self.table.setItem(row, 3, QTableWidgetItem(s.get("label", "") or "Untitled"))
            self.table.setItem(row, 4, QTableWidgetItem(s.get("message", "") or "—"))
            self.table.setItem(row, 5, QTableWidgetItem(s["created_at"]))

    def _load_apply_history(self):
        records = self.store.get_apply_history(50)
        self.apply_table.setRowCount(len(records))

        for row, r in enumerate(records):
            self.apply_table.setItem(row, 0, QTableWidgetItem(r.get("obj_type", "")))
            self.apply_table.setItem(row, 1, QTableWidgetItem(r.get("obj_name", "")))

            status_item = QTableWidgetItem(r.get("status", ""))
            if r.get("status") == "success":
                status_item.setForeground(QColor("#22c55e"))
            else:
                status_item.setForeground(QColor("#ef4444"))
            self.apply_table.setItem(row, 2, status_item)

            self.apply_table.setItem(row, 3, QTableWidgetItem(r.get("error_message", "") or "—"))
            self.apply_table.setItem(row, 4, QTableWidgetItem(r.get("applied_at", "")))

    def _compare_selected(self):
        selected = self.table.selectionModel().selectedRows()
        if len(selected) != 2:
            QMessageBox.warning(self, "Select Two", "Please select exactly 2 snapshots to compare.\n"
                "Hold Ctrl and click to multi-select.")
            return

        id1 = self.table.item(selected[0].row(), 1).text()
        id2 = self.table.item(selected[1].row(), 1).text()

        # Find full IDs
        snapshots = self.store.get_snapshots()
        full1 = next((s["id"] for s in snapshots if s["id"].startswith(id1)), None)
        full2 = next((s["id"] for s in snapshots if s["id"].startswith(id2)), None)

        if not full1 or not full2:
            QMessageBox.critical(self, "Error", "Could not find selected snapshots.")
            return

        # Navigate to compare page — parent is MainWindow
        main_win = self.window()
        if hasattr(main_win, "compare_page") and hasattr(main_win, "_switch_page"):
            main_win.compare_page.mode_combo.setCurrentIndex(0)
            main_win.compare_page._load_combos()
            # Set source and target
            for i in range(main_win.compare_page.source_combo.count()):
                if main_win.compare_page.source_combo.itemData(i) == full1:
                    main_win.compare_page.source_combo.setCurrentIndex(i)
                    break
            for i in range(main_win.compare_page.target_combo.count()):
                if main_win.compare_page.target_combo.itemData(i) == full2:
                    main_win.compare_page.target_combo.setCurrentIndex(i)
                    break
            main_win._switch_page(2)
            main_win.compare_page._run_compare()
