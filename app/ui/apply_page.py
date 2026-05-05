"""
Apply Page — apply schema changes to a target database.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QGroupBox, QScrollArea, QCheckBox,
)
from PyQt6.QtCore import Qt

from app.services.snapshot_store import SnapshotStore
from app.services.validators import build_connection_string
from app.services.db_factory import get_engine
from app.services.executor import apply_sql
from app.services.history import compare_snapshots, compare_live_vs_snapshot
from app.services.introspection import fetch_tables, fetch_objects
from app.services.errors import AppError
from app.ui.diff_viewer import DiffViewer
from app.logger import get_logger

log = get_logger("apply")

APPLY_ORDER = ["tables", "functions", "views", "triggers"]


class ApplyPage(QWidget):
    def __init__(self, store: SnapshotStore):
        super().__init__()
        self.store = store
        self.pending_diffs = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Apply Changes")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel("Select a source snapshot and target DB to apply missing objects in safe order.")
        subtitle.setObjectName("sectionSubtitle")
        layout.addWidget(subtitle)

        # ── Config ───────────────────────────────────────────────────
        config_group = QGroupBox("Configuration")
        cg_layout = QVBoxLayout(config_group)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("Source Snapshot:"))
        self.snap_combo = QComboBox()
        self.snap_combo.setMinimumWidth(350)
        r1.addWidget(self.snap_combo)
        r1.addStretch()
        cg_layout.addLayout(r1)

        r2 = QHBoxLayout()
        r2.addWidget(QLabel("Target Connection:"))
        self.target_combo = QComboBox()
        self.target_combo.setMinimumWidth(350)
        r2.addWidget(self.target_combo)
        r2.addStretch()
        cg_layout.addLayout(r2)

        btn_row = QHBoxLayout()
        load_btn = QPushButton("🔍 Load Differences")
        load_btn.setProperty("cssClass", "primary")
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(self._load_diffs)
        btn_row.addWidget(load_btn)
        btn_row.addStretch()
        cg_layout.addLayout(btn_row)

        layout.addWidget(config_group)

        # ── Results ──────────────────────────────────────────────────
        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(12)
        self.results_area.setWidget(self.results_widget)
        layout.addWidget(self.results_area)

        # ── Apply All Button ─────────────────────────────────────────
        self.apply_all_btn = QPushButton("⚡ Apply All (Safe Order)")
        self.apply_all_btn.setProperty("cssClass", "primary")
        self.apply_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_all_btn.clicked.connect(self._apply_all)
        self.apply_all_btn.setVisible(False)
        layout.addWidget(self.apply_all_btn)

        self.status_label = QLabel("")
        self.status_label.setObjectName("sectionSubtitle")
        layout.addWidget(self.status_label)

    def refresh(self):
        self.snap_combo.clear()
        self.target_combo.clear()
        for s in self.store.get_snapshots():
            label = f"{s['id'][:8]} — {s.get('label','Untitled')} ({s.get('connection_name','?')})"
            self.snap_combo.addItem(label, s["id"])
        for c in self.store.get_connections():
            self.target_combo.addItem(f"{c['name']} ({c['db_type']})", c["id"])

    def _load_diffs(self):
        snap_id = self.snap_combo.currentData()
        target_id = self.target_combo.currentData()
        if not snap_id or not target_id:
            QMessageBox.warning(self, "Missing", "Select both snapshot and target.")
            return

        try:
            target_conn = self.store.get_connection(target_id)
            cs = build_connection_string(target_conn["db_type"], target_conn["host"],
                target_conn["port"], target_conn["database_name"],
                target_conn["username"], target_conn["password_encrypted"])
            engine = get_engine(cs)
            tables = fetch_tables(engine, target_conn["db_type"])
            objects = fetch_objects(engine, target_conn["db_type"])
            engine.dispose()

            diffs = compare_live_vs_snapshot(self.store, snap_id, tables, objects)
            # Only show missing_in_source (things in snapshot but not in live target)
            # and modified items
            applicable = [d for d in diffs if d["status"] in ("missing_in_source", "modified")]

            self.pending_diffs = applicable
            self._render_apply_list(applicable)
            self.apply_all_btn.setVisible(len(applicable) > 0)
            self.status_label.setText(f"{len(applicable)} change(s) can be applied")

        except AppError as e:
            QMessageBox.critical(self, "Error", f"❌ {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ {e}")
            log.error("Load diffs error: %s", e, exc_info=True)

    def _render_apply_list(self, diffs):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not diffs:
            lbl = QLabel("✅ Target database is up to date!")
            lbl.setStyleSheet("font-size:16px; padding:20px; color:#22c55e;")
            self.results_layout.addWidget(lbl)
            return

        for diff in diffs:
            card = QGroupBox(f"{diff['name']} ({diff['type']})")
            cl = QVBoxLayout(card)

            status = diff["status"]
            badge = QLabel(status.replace("_", " ").upper())
            if "missing" in status:
                badge.setObjectName("badgeMissing")
            else:
                badge.setObjectName("badgeModified")
            cl.addWidget(badge)

            viewer = DiffViewer(diff["source_sql"], diff["target_sql"])
            viewer.setMinimumHeight(200)
            viewer.setMaximumHeight(300)
            cl.addWidget(viewer)

            apply_btn = QPushButton(f"⚡ Apply {diff['name']}")
            apply_btn.setProperty("cssClass", "primary")
            apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            apply_btn.clicked.connect(lambda _, d=diff, b=apply_btn: self._apply_single(d, b))
            cl.addWidget(apply_btn)

            self.results_layout.addWidget(card)

        self.results_layout.addStretch()

    def _apply_single(self, diff, btn):
        target_id = self.target_combo.currentData()
        if not target_id:
            return

        reply = QMessageBox.question(self, "Confirm",
            f"Apply {diff['type']} '{diff['name']}' to target database?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            target_conn = self.store.get_connection(target_id)
            cs = build_connection_string(target_conn["db_type"], target_conn["host"],
                target_conn["port"], target_conn["database_name"],
                target_conn["username"], target_conn["password_encrypted"])
            engine = get_engine(cs)

            sql = diff["target_sql"] if diff["status"] == "missing_in_source" else diff["source_sql"]
            apply_sql(engine, sql, diff["type"])
            engine.dispose()

            self.store.save_apply_record(target_id, sql, diff["type"], diff["name"], "success")
            btn.setText("✅ Applied")
            btn.setEnabled(False)
            log.info("Applied %s '%s' successfully", diff["type"], diff["name"])

        except AppError as e:
            self.store.save_apply_record(target_id, "", diff["type"], diff["name"], "error", e.message)
            QMessageBox.critical(self, "Failed", f"❌ {e.message}")
        except Exception as e:
            self.store.save_apply_record(target_id, "", diff["type"], diff["name"], "error", str(e))
            QMessageBox.critical(self, "Error", f"❌ {e}")

    def _apply_all(self):
        target_id = self.target_combo.currentData()
        if not target_id or not self.pending_diffs:
            return

        reply = QMessageBox.question(self, "Confirm Bulk Apply",
            f"Apply all {len(self.pending_diffs)} changes in safe order?\n\n"
            "Order: tables → functions → views → triggers",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            target_conn = self.store.get_connection(target_id)
            cs = build_connection_string(target_conn["db_type"], target_conn["host"],
                target_conn["port"], target_conn["database_name"],
                target_conn["username"], target_conn["password_encrypted"])
            engine = get_engine(cs)

            ordered = sorted(self.pending_diffs,
                key=lambda d: APPLY_ORDER.index(d["type"]) if d["type"] in APPLY_ORDER else 99)

            success = 0
            errors = []

            for diff in ordered:
                try:
                    sql = diff["target_sql"] if diff["status"] == "missing_in_source" else diff["source_sql"]
                    apply_sql(engine, sql, diff["type"])
                    self.store.save_apply_record(target_id, sql, diff["type"], diff["name"], "success")
                    success += 1
                except AppError as e:
                    self.store.save_apply_record(target_id, "", diff["type"], diff["name"], "error", e.message)
                    errors.append(f"{diff['name']}: {e.message}")

            engine.dispose()

            msg = f"✅ {success} applied successfully."
            if errors:
                msg += f"\n\n❌ {len(errors)} failed:\n" + "\n".join(errors)
            QMessageBox.information(self, "Apply Results", msg)
            log.info("Bulk apply: %d success, %d errors", success, len(errors))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ {e}")
            log.error("Bulk apply error: %s", e, exc_info=True)
