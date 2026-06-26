"""
Apply Page — apply schema changes to a target database.
Professional UI with clear source/target indicators and progress tracking.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QGroupBox, QScrollArea, QCheckBox,
    QFrame, QProgressBar, QSizePolicy,
)
from PyQt6.QtCore import Qt

from app.services.snapshot_store import SnapshotStore
from app.services.validators import build_connection_string
from app.services.db_factory import get_engine
from app.services.executor import apply_sql
from app.services.history import compare_snapshots, compare_live_vs_snapshot
from app.services.introspection import fetch_tables, fetch_objects, OBJECT_TYPES
from app.services.errors import AppError
from app.ui.diff_viewer import DiffViewer
from app.logger import get_logger

log = get_logger("apply")

APPLY_ORDER = ["tables"] + list(OBJECT_TYPES)

# Human-readable names
_TYPE_LABELS = {
    "tables": "Tables",
    "functions": "Functions",
    "procedures": "Procedures",
    "aggregates": "Aggregates",
    "views": "Views",
    "materialized_views": "Mat. Views",
    "triggers": "Triggers",
    "sequences": "Sequences",
}

# Status badge config
_STATUS_CONFIG = {
    "missing_in_source": ("badgeMissingSource", "⚠ MISSING IN TARGET DB", "This object is in the snapshot but not in the live target — it will be created."),
    "modified":          ("badgeModified",       "✎ MODIFIED",            "This object differs between snapshot and live target — it will be updated."),
}


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
        subtitle = QLabel("Select a source snapshot and target DB to apply missing or modified objects in safe dependency order.")
        subtitle.setObjectName("sectionSubtitle")
        layout.addWidget(subtitle)

        # ── Config ───────────────────────────────────────────────────
        config_group = QGroupBox("Configuration")
        cg_layout = QVBoxLayout(config_group)
        cg_layout.setSpacing(10)

        r1 = QHBoxLayout()
        src_label = QLabel("📸  Source Snapshot:")
        src_label.setMinimumWidth(150)
        src_label.setStyleSheet("font-weight: 600;")
        r1.addWidget(src_label)
        self.snap_combo = QComboBox()
        self.snap_combo.setMinimumWidth(350)
        r1.addWidget(self.snap_combo)
        r1.addStretch()
        cg_layout.addLayout(r1)

        r2 = QHBoxLayout()
        tgt_label = QLabel("🎯  Target Connection:")
        tgt_label.setMinimumWidth(150)
        tgt_label.setStyleSheet("font-weight: 600;")
        r2.addWidget(tgt_label)
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

        # ── Summary Stats ────────────────────────────────────────────
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(
            "background: rgba(30, 41, 59, 120); border: 1px solid #334155; border-radius: 12px;"
        )
        self.stats_frame.setVisible(False)
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(16, 10, 16, 10)

        self.stat_total = self._make_stat("0", "Applicable")
        self.stat_missing = self._make_stat("0", "Missing in Target")
        self.stat_modified = self._make_stat("0", "Modified")

        stats_layout.addWidget(self.stat_total)
        stats_layout.addWidget(self._make_divider())
        stats_layout.addWidget(self.stat_missing)
        stats_layout.addWidget(self._make_divider())
        stats_layout.addWidget(self.stat_modified)
        stats_layout.addStretch()

        layout.addWidget(self.stats_frame)

        # ── Results ──────────────────────────────────────────────────
        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(12)
        self.results_area.setWidget(self.results_widget)
        layout.addWidget(self.results_area)

        # ── Apply All Button ─────────────────────────────────────────
        bottom_bar = QHBoxLayout()

        self.apply_all_btn = QPushButton("⚡ Apply All (Safe Order)")
        self.apply_all_btn.setProperty("cssClass", "primary")
        self.apply_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.apply_all_btn.clicked.connect(self._apply_all)
        self.apply_all_btn.setVisible(False)
        self.apply_all_btn.setMinimumHeight(40)
        bottom_bar.addWidget(self.apply_all_btn)

        bottom_bar.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("sectionSubtitle")
        bottom_bar.addWidget(self.status_label)

        layout.addLayout(bottom_bar)

    # ── Helpers ──────────────────────────────────────────────────
    @staticmethod
    def _make_stat(number, label):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 0, 12, 0)
        l.setSpacing(2)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        n = QLabel(number)
        n.setObjectName("statNumber")
        n.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb = QLabel(label)
        lb.setObjectName("statLabel")
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l.addWidget(n)
        l.addWidget(lb)
        w._num_label = n
        return w

    @staticmethod
    def _make_divider():
        d = QFrame()
        d.setFixedWidth(1)
        d.setStyleSheet("background-color: #334155;")
        d.setFixedHeight(40)
        return d

    def _update_stats(self, diffs):
        n_missing = sum(1 for d in diffs if d["status"] == "missing_in_source")
        n_mod = sum(1 for d in diffs if d["status"] == "modified")
        self.stat_total._num_label.setText(str(len(diffs)))
        self.stat_missing._num_label.setText(str(n_missing))
        self.stat_modified._num_label.setText(str(n_mod))
        self.stats_frame.setVisible(len(diffs) > 0)

    # ── Data Loading ─────────────────────────────────────────────
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
            self._update_stats(applicable)
            self._render_apply_list(applicable)
            self.apply_all_btn.setVisible(len(applicable) > 0)
            self.status_label.setText(f"{len(applicable)} change(s) can be applied")

        except AppError as e:
            QMessageBox.critical(self, "Error", f"❌ {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ {e}")
            log.error("Load diffs error: %s", e, exc_info=True)

    # ── Render ───────────────────────────────────────────────────
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
            card = QGroupBox()
            card.setProperty("diffStatus", diff["status"])
            card.style().unpolish(card)
            card.style().polish(card)
            cl = QVBoxLayout(card)
            cl.setSpacing(8)

            # ── Header ───────────────────────────────────────────
            header = QHBoxLayout()
            header.setSpacing(10)

            name_label = QLabel(f"<b style='font-size:14px'>{diff['name']}</b>")
            name_label.setTextFormat(Qt.TextFormat.RichText)
            header.addWidget(name_label)

            # Type tag
            type_display = _TYPE_LABELS.get(diff["type"], diff["type"].replace("_", " ").title())
            type_tag = QLabel(type_display.upper())
            type_tag.setObjectName("badgeTypeTag")
            type_tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
            type_tag.setFixedHeight(22)
            header.addWidget(type_tag)

            header.addStretch()

            # Status badge
            status = diff["status"]
            cfg = _STATUS_CONFIG.get(status, ("badgeModified", status.upper(), ""))
            badge = QLabel(cfg[1])
            badge.setObjectName(cfg[0])
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedHeight(26)
            badge.setToolTip(cfg[2])
            header.addWidget(badge)

            cl.addLayout(header)

            # ── Direction indicator ──────────────────────────────
            if status == "missing_in_source":
                direction = QLabel("📦  Snapshot → Target DB  —  this object will be CREATED in the target")
                direction.setStyleSheet("color: #fbbf24; font-size: 11px; padding: 2px 4px; font-style: italic;")
                cl.addWidget(direction)
            elif status == "modified":
                direction = QLabel("🔄  Snapshot → Target DB  —  this object will be UPDATED in the target")
                direction.setStyleSheet("color: #60a5fa; font-size: 11px; padding: 2px 4px; font-style: italic;")
                cl.addWidget(direction)

            # ── Diff viewer ──────────────────────────────────────
            viewer = DiffViewer(diff["source_sql"], diff["target_sql"])
            viewer.setMinimumHeight(180)
            viewer.setMaximumHeight(300)
            cl.addWidget(viewer)

            # ── Apply button ─────────────────────────────────────
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            apply_btn = QPushButton(f"⚡ Apply '{diff['name']}'")
            apply_btn.setProperty("cssClass", "primary")
            apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            apply_btn.setMinimumWidth(200)
            apply_btn.clicked.connect(lambda _, d=diff, b=apply_btn: self._apply_single(d, b))
            btn_row.addWidget(apply_btn)
            cl.addLayout(btn_row)

            self.results_layout.addWidget(card)

        self.results_layout.addStretch()

    # ── Apply Actions ────────────────────────────────────────────
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
            btn.setProperty("cssClass", "secondary")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
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

        order_str = " → ".join(APPLY_ORDER)
        reply = QMessageBox.question(self, "Confirm Bulk Apply",
            f"Apply all {len(self.pending_diffs)} changes in safe order?\n\n"
            f"Order: {order_str}",
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

            # Refresh the list to show updated state
            if success > 0:
                self._load_diffs()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ {e}")
            log.error("Bulk apply error: %s", e, exc_info=True)
