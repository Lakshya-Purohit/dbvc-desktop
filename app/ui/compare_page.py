"""
Compare Page — compare snapshots or live databases with diff viewer.
Dynamic filter tabs, clear source/target indicators, summary stats.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QScrollArea, QGroupBox, QMessageBox, QSizePolicy,
    QFrame,
)
from PyQt6.QtCore import Qt

from app.services.snapshot_store import SnapshotStore
from app.services.validators import build_connection_string
from app.services.db_factory import get_engine
from app.services.introspection import fetch_tables, fetch_objects, OBJECT_TYPES
from app.services.normalizer import normalize
from app.services.sql_generator import generate_create_table_sql
from app.services.history import compare_snapshots, compare_live_vs_snapshot
from app.services.errors import AppError
from app.ui.diff_viewer import DiffViewer
from app.logger import get_logger

log = get_logger("compare")

# Human-readable names for filter pills
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

# Status badge config: (objectName, display text, icon)
_STATUS_CONFIG = {
    "missing_in_source": ("badgeMissingSource", "⚠ ONLY IN TARGET", "Object exists in target but is missing from source"),
    "missing_in_target": ("badgeMissingTarget", "⚠ ONLY IN SOURCE", "Object exists in source but is missing from target"),
    "modified":          ("badgeModified",       "✎ MODIFIED",       "Object differs between source and target"),
}


class ComparePage(QWidget):
    def __init__(self, store: SnapshotStore):
        super().__init__()
        self.store = store
        self.current_diffs = []
        self._active_filter = "All"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)

        title = QLabel("Compare Schemas")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel("Compare snapshots or live databases side-by-side — like git diff.")
        subtitle.setObjectName("sectionSubtitle")
        layout.addWidget(subtitle)

        # ── Mode Selector ────────────────────────────────────────────
        mode_group = QGroupBox("Comparison Mode")
        mode_layout = QVBoxLayout(mode_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Snapshot ↔ Snapshot",
            "Live DB ↔ Snapshot",
            "Live DB ↔ Live DB",
        ])
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        row1.addWidget(self.mode_combo)
        row1.addStretch()
        mode_layout.addLayout(row1)

        # Source row
        row2 = QHBoxLayout()
        self.source_label = QLabel("Source Snapshot:")
        self.source_label.setMinimumWidth(160)
        row2.addWidget(self.source_label)
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(350)
        row2.addWidget(self.source_combo)
        row2.addStretch()
        mode_layout.addLayout(row2)

        # Target row
        row3 = QHBoxLayout()
        self.target_label = QLabel("Target Snapshot:")
        self.target_label.setMinimumWidth(160)
        row3.addWidget(self.target_label)
        self.target_combo = QComboBox()
        self.target_combo.setMinimumWidth(350)
        row3.addWidget(self.target_combo)
        row3.addStretch()
        mode_layout.addLayout(row3)

        compare_btn = QPushButton("🔍 Compare")
        compare_btn.setProperty("cssClass", "primary")
        compare_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        compare_btn.clicked.connect(self._run_compare)
        mode_layout.addWidget(compare_btn)

        layout.addWidget(mode_group)

        # ── Summary Stats Bar ────────────────────────────────────────
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(
            "background: rgba(30, 41, 59, 120); border: 1px solid #334155; border-radius: 12px; padding: 8px;"
        )
        self.stats_frame.setVisible(False)
        stats_layout = QHBoxLayout(self.stats_frame)
        stats_layout.setContentsMargins(16, 8, 16, 8)

        self.stat_total = self._make_stat("0", "Total")
        self.stat_source = self._make_stat("0", "Only in Source")
        self.stat_target = self._make_stat("0", "Only in Target")
        self.stat_modified = self._make_stat("0", "Modified")

        stats_layout.addWidget(self.stat_total)
        stats_layout.addWidget(self._make_divider())
        stats_layout.addWidget(self.stat_source)
        stats_layout.addWidget(self._make_divider())
        stats_layout.addWidget(self.stat_target)
        stats_layout.addWidget(self._make_divider())
        stats_layout.addWidget(self.stat_modified)
        stats_layout.addStretch()

        layout.addWidget(self.stats_frame)

        # ── Filter Tabs ──────────────────────────────────────────────
        self.filter_layout = QHBoxLayout()
        self.filter_layout.setSpacing(6)
        self.filter_btns: list[QPushButton] = []
        # Will be rebuilt dynamically when diffs arrive
        self._build_filter_tabs([])
        layout.addLayout(self.filter_layout)

        # ── Results Scroll Area ──────────────────────────────────────
        self.results_area = QScrollArea()
        self.results_area.setWidgetResizable(True)
        self.results_widget = QWidget()
        self.results_layout = QVBoxLayout(self.results_widget)
        self.results_layout.setSpacing(16)
        self.results_area.setWidget(self.results_widget)
        layout.addWidget(self.results_area)

        # Summary label
        self.summary_label = QLabel("")
        self.summary_label.setObjectName("sectionSubtitle")
        layout.addWidget(self.summary_label)

        self._mode_changed()

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
        n_source = sum(1 for d in diffs if d["status"] == "missing_in_target")
        n_target = sum(1 for d in diffs if d["status"] == "missing_in_source")
        n_mod = sum(1 for d in diffs if d["status"] == "modified")
        self.stat_total._num_label.setText(str(len(diffs)))
        self.stat_source._num_label.setText(str(n_source))
        self.stat_target._num_label.setText(str(n_target))
        self.stat_modified._num_label.setText(str(n_mod))
        self.stats_frame.setVisible(len(diffs) > 0)

    # ── Filter Tabs ──────────────────────────────────────────────
    def _build_filter_tabs(self, diffs):
        """Rebuild filter tabs dynamically based on what object types appear."""
        # Clear existing
        for btn in self.filter_btns:
            self.filter_layout.removeWidget(btn)
            btn.deleteLater()
        self.filter_btns.clear()

        # Count per type
        type_counts: dict[str, int] = {}
        for d in diffs:
            t = d["type"]
            type_counts[t] = type_counts.get(t, 0) + 1

        # Build "All" + each type that has diffs
        tabs = [("All", len(diffs))]
        all_types = ["tables"] + list(OBJECT_TYPES)
        for t in all_types:
            if t in type_counts:
                label = _TYPE_LABELS.get(t, t.replace("_", " ").title())
                tabs.append((label, type_counts[t]))

        for label, count in tabs:
            btn = QPushButton(f"{label}  ({count})" if count else label)
            btn.setCheckable(True)
            btn.setProperty("cssClass", "filterPill")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, l=label: self._filter(l))
            self.filter_layout.addWidget(btn)
            self.filter_btns.append(btn)

        # Spacer at the end
        self.filter_layout.addStretch()

        # Highlight the active one
        self._highlight_active_filter()

    def _highlight_active_filter(self):
        for btn in self.filter_btns:
            text = btn.text().split("  (")[0]
            is_active = text == self._active_filter
            btn.setChecked(is_active)
            # Force style refresh by toggling the property
            btn.setProperty("cssClass", "filterPillActive" if is_active else "filterPill")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # ── Data / Combo Loading ─────────────────────────────────────
    def refresh(self):
        self._load_combos()

    def _load_combos(self):
        mode = self.mode_combo.currentIndex()
        self.source_combo.clear()
        self.target_combo.clear()

        if mode == 0:  # Snap ↔ Snap
            snapshots = self.store.get_snapshots()
            for s in snapshots:
                label = f"{s['id'][:8]} — {s.get('label', 'Untitled')} ({s.get('connection_name', '?')}) [{s['created_at']}]"
                self.source_combo.addItem(label, s["id"])
                self.target_combo.addItem(label, s["id"])
        elif mode == 1:  # Live ↔ Snap
            conns = self.store.get_connections()
            for c in conns:
                self.source_combo.addItem(f"{c['name']} ({c['db_type']})", c["id"])
            snapshots = self.store.get_snapshots()
            for s in snapshots:
                label = f"{s['id'][:8]} — {s.get('label', 'Untitled')} [{s['created_at']}]"
                self.target_combo.addItem(label, s["id"])
        elif mode == 2:  # Live ↔ Live
            conns = self.store.get_connections()
            for c in conns:
                label = f"{c['name']} ({c['db_type']})"
                self.source_combo.addItem(label, c["id"])
                self.target_combo.addItem(label, c["id"])

    def _mode_changed(self):
        mode = self.mode_combo.currentIndex()
        labels = [
            ("Source Snapshot:", "Target Snapshot:"),
            ("Live DB Connection:", "Compare Against Snapshot:"),
            ("Source DB:", "Target DB:"),
        ]
        self.source_label.setText(labels[mode][0])
        self.target_label.setText(labels[mode][1])
        self._load_combos()

    # ── Compare ──────────────────────────────────────────────────
    def _run_compare(self):
        mode = self.mode_combo.currentIndex()
        source_id = self.source_combo.currentData()
        target_id = self.target_combo.currentData()

        if not source_id or not target_id:
            QMessageBox.warning(self, "Missing", "Please select both source and target.")
            return

        log.info("Running comparison (mode=%d)...", mode)

        try:
            if mode == 0:  # Snap ↔ Snap
                diffs = compare_snapshots(self.store, source_id, target_id)
            elif mode == 1:  # Live ↔ Snap
                conn = self.store.get_connection(source_id)
                cs = build_connection_string(conn["db_type"], conn["host"], conn["port"],
                    conn["database_name"], conn["username"], conn["password_encrypted"])
                engine = get_engine(cs)
                tables = fetch_tables(engine, conn["db_type"])
                objects = fetch_objects(engine, conn["db_type"])
                engine.dispose()
                diffs = compare_live_vs_snapshot(self.store, target_id, tables, objects)
            elif mode == 2:  # Live ↔ Live
                diffs = self._compare_live(source_id, target_id)

            self.current_diffs = diffs
            self._active_filter = "All"
            self._build_filter_tabs(diffs)
            self._update_stats(diffs)
            self._render_diffs(diffs)
            self.summary_label.setText(f"Found {len(diffs)} difference(s)")
            log.info("Comparison complete: %d diffs", len(diffs))

        except AppError as e:
            QMessageBox.critical(self, "Error", f"❌ {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ {e}")
            log.error("Compare error: %s", e, exc_info=True)

    def _compare_live(self, source_conn_id, target_conn_id):
        sc = self.store.get_connection(source_conn_id)
        tc = self.store.get_connection(target_conn_id)

        cs1 = build_connection_string(sc["db_type"], sc["host"], sc["port"],
            sc["database_name"], sc["username"], sc["password_encrypted"])
        cs2 = build_connection_string(tc["db_type"], tc["host"], tc["port"],
            tc["database_name"], tc["username"], tc["password_encrypted"])

        e1 = get_engine(cs1)
        e2 = get_engine(cs2)

        t1 = fetch_tables(e1, sc["db_type"])
        t2 = fetch_tables(e2, tc["db_type"])
        o1 = fetch_objects(e1, sc["db_type"])
        o2 = fetch_objects(e2, tc["db_type"])
        e1.dispose()
        e2.dispose()

        diffs = []
        # Tables
        for name in set(t1.keys()) | set(t2.keys()):
            if name in t1 and name not in t2:
                diffs.append({"type":"tables","name":name,"status":"missing_in_target",
                    "source_sql":generate_create_table_sql(name, t1[name]),"target_sql":""})
            elif name in t2 and name not in t1:
                diffs.append({"type":"tables","name":name,"status":"missing_in_source",
                    "source_sql":"","target_sql":generate_create_table_sql(name, t2[name])})
            else:
                s1 = generate_create_table_sql(name, t1[name])
                s2 = generate_create_table_sql(name, t2[name])
                if s1 != s2:
                    diffs.append({"type":"tables","name":name,"status":"modified","source_sql":s1,"target_sql":s2})
        # Objects
        for ot in OBJECT_TYPES:
            d1 = o1.get(ot, {})
            d2 = o2.get(ot, {})
            for name in set(d1.keys()) | set(d2.keys()):
                if name in d1 and name not in d2:
                    diffs.append({"type":ot,"name":name,"status":"missing_in_target",
                        "source_sql":normalize(d1[name]),"target_sql":""})
                elif name in d2 and name not in d1:
                    diffs.append({"type":ot,"name":name,"status":"missing_in_source",
                        "source_sql":"","target_sql":normalize(d2[name])})
                else:
                    s1, s2 = normalize(d1[name]), normalize(d2[name])
                    if s1 != s2:
                        diffs.append({"type":ot,"name":name,"status":"modified","source_sql":s1,"target_sql":s2})
        return diffs

    # ── Render Diffs ─────────────────────────────────────────────
    def _render_diffs(self, diffs, type_filter="All"):
        # Clear previous
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not diffs:
            lbl = QLabel("✅ Schemas are fully in sync!")
            lbl.setStyleSheet("font-size:16px; padding:20px; color:#22c55e;")
            self.results_layout.addWidget(lbl)
            return

        rendered = 0
        for diff in diffs:
            if type_filter != "All":
                type_label = _TYPE_LABELS.get(diff["type"], diff["type"].replace("_", " ").title())
                if type_label != type_filter:
                    continue

            card = QGroupBox()
            card.setProperty("diffStatus", diff["status"])
            # Force style to pick up the dynamic property
            card.style().unpolish(card)
            card.style().polish(card)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(8)

            # ── Card Header ──────────────────────────────────────
            header = QHBoxLayout()
            header.setSpacing(10)

            # Object name
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

            # Status badge with direction
            status = diff["status"]
            cfg = _STATUS_CONFIG.get(status, ("badgeSynced", status.upper(), ""))
            badge = QLabel(cfg[1])
            badge.setObjectName(cfg[0])
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedHeight(26)
            badge.setToolTip(cfg[2])
            header.addWidget(badge)

            card_layout.addLayout(header)

            # ── Direction indicator for missing objects ───────────
            if status == "missing_in_target":
                direction = QLabel("◀ SOURCE only — object does not exist in target")
                direction.setStyleSheet("color: #fbbf24; font-size: 11px; padding: 2px 4px; font-style: italic;")
                card_layout.addWidget(direction)
            elif status == "missing_in_source":
                direction = QLabel("▶ TARGET only — object does not exist in source")
                direction.setStyleSheet("color: #fb923c; font-size: 11px; padding: 2px 4px; font-style: italic;")
                card_layout.addWidget(direction)

            # ── Diff viewer ──────────────────────────────────────
            viewer = DiffViewer(diff["source_sql"], diff["target_sql"])
            viewer.setMinimumHeight(280)
            card_layout.addWidget(viewer)

            self.results_layout.addWidget(card)
            rendered += 1

        if rendered == 0 and type_filter != "All":
            lbl = QLabel(f"No {type_filter.lower()} differences found.")
            lbl.setStyleSheet("font-size:14px; padding:16px; color:#64748b;")
            self.results_layout.addWidget(lbl)

        self.results_layout.addStretch()

    def _filter(self, label):
        self._active_filter = label
        self._highlight_active_filter()
        self._render_diffs(self.current_diffs, label)
