"""
Snapshot Page — take schema snapshots and browse history.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QGroupBox,
)
from PyQt6.QtCore import Qt

from app.services.snapshot_store import SnapshotStore
from app.services.validators import build_connection_string
from app.services.db_factory import get_engine
from app.services.introspection import fetch_tables, fetch_objects
from app.services.errors import AppError
from app.logger import get_logger

log = get_logger("snapshots")


class SnapshotPage(QWidget):
    def __init__(self, store: SnapshotStore):
        super().__init__()
        self.store = store
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Schema Snapshots")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel("Capture your database schema at a point in time — like a git commit.")
        subtitle.setObjectName("sectionSubtitle")
        layout.addWidget(subtitle)

        # ── Take Snapshot Group ──────────────────────────────────────
        snap_group = QGroupBox("Take New Snapshot")
        sg_layout = QVBoxLayout(snap_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Connection:"))
        self.conn_combo = QComboBox()
        self.conn_combo.setMinimumWidth(300)
        row1.addWidget(self.conn_combo)
        row1.addStretch()
        sg_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Label:"))
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("e.g. v1.2 release, pre-migration...")
        row2.addWidget(self.label_input)
        sg_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Message:"))
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Optional description of this snapshot")
        row3.addWidget(self.message_input)
        sg_layout.addLayout(row3)

        snap_btn = QPushButton("📸 Take Snapshot")
        snap_btn.setProperty("cssClass", "primary")
        snap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        snap_btn.clicked.connect(self._take_snapshot)
        sg_layout.addWidget(snap_btn)

        layout.addWidget(snap_group)

        # ── Snapshot History ─────────────────────────────────────────
        history_label = QLabel("Snapshot History")
        history_label.setObjectName("sectionTitle")
        history_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(history_label)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by connection:"))
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Connections", "")
        self.filter_combo.currentIndexChanged.connect(self._load_snapshots)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.snap_table = QTableWidget()
        self.snap_table.setColumnCount(5)
        self.snap_table.setHorizontalHeaderLabels(["ID", "Connection", "Label", "Created At", "Actions"])
        self.snap_table.setColumnWidth(4, 120)
        self.snap_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.snap_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.snap_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.snap_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.snap_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.snap_table.setAlternatingRowColors(True)
        self.snap_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.snap_table.verticalHeader().setVisible(False)
        layout.addWidget(self.snap_table)

        self.refresh()

    def refresh(self):
        self._load_connections()
        self._load_snapshots()

    def _load_connections(self):
        self.conn_combo.clear()
        self.filter_combo.clear()
        self.filter_combo.addItem("All Connections", "")
        conns = self.store.get_connections()
        for c in conns:
            label = f"{c['name']} ({c['db_type']})"
            self.conn_combo.addItem(label, c["id"])
            self.filter_combo.addItem(label, c["id"])

    def _load_snapshots(self):
        conn_id = self.filter_combo.currentData() or None
        snapshots = self.store.get_snapshots(conn_id)
        self.snap_table.setRowCount(len(snapshots))

        for row, s in enumerate(snapshots):
            self.snap_table.setItem(row, 0, QTableWidgetItem(s["id"][:8]))
            self.snap_table.setItem(row, 1, QTableWidgetItem(s.get("connection_name", "—")))
            self.snap_table.setItem(row, 2, QTableWidgetItem(s["label"] or "Untitled"))
            self.snap_table.setItem(row, 3, QTableWidgetItem(s["created_at"]))

            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            del_btn = QPushButton("🗑️")
            del_btn.setFixedSize(36, 30)
            del_btn.setProperty("cssClass", "danger")
            del_btn.clicked.connect(lambda _, sid=s["id"]: self._delete_snapshot(sid))
            al.addWidget(del_btn)
            self.snap_table.setCellWidget(row, 4, actions)

    def _take_snapshot(self):
        conn_id = self.conn_combo.currentData()
        if not conn_id:
            QMessageBox.warning(self, "No Connection", "Please select a connection first.")
            return

        conn = self.store.get_connection(conn_id)
        if not conn:
            QMessageBox.critical(self, "Error", "Connection not found.")
            return

        label = self.label_input.text().strip()
        message = self.message_input.text().strip()

        log.info("Taking snapshot for '%s' (label=%s)...", conn["name"], label)

        try:
            conn_str = build_connection_string(
                conn["db_type"], conn["host"], conn["port"],
                conn["database_name"], conn["username"], conn["password_encrypted"],
            )
            engine = get_engine(conn_str)

            tables = fetch_tables(engine, conn["db_type"])
            objects = fetch_objects(engine, conn["db_type"])
            engine.dispose()

            schema_data = {"tables": tables, **objects}
            total = len(tables) + sum(len(v) for v in objects.values())

            sid = self.store.save_snapshot(conn_id, schema_data, label, message)

            self.label_input.clear()
            self.message_input.clear()
            self._load_snapshots()

            QMessageBox.information(
                self, "Snapshot Saved",
                f"✅ Snapshot {sid[:8]} saved!\n{total} objects captured."
            )
            log.info("Snapshot complete: %s — %d objects", sid[:8], total)

        except AppError as e:
            QMessageBox.critical(self, "Error", f"❌ {e.message}")
            log.error("Snapshot failed: %s", e.message)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ {e}")
            log.error("Snapshot error: %s", e, exc_info=True)

    def _delete_snapshot(self, snap_id):
        r = QMessageBox.question(self, "Delete Snapshot",
            f"Delete snapshot {snap_id[:8]}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.store.delete_snapshot(snap_id)
            self._load_snapshots()
