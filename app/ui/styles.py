"""
QSS Dark Theme — matches the glassmorphism web UI aesthetic.
"""

DARK_THEME = """
/* ── Global ──────────────────────────────────────────────── */
QWidget {
    background-color: #0f172a;
    color: #e5e7eb;
    font-family: "Segoe UI", "Inter", system-ui, sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #020617;
}

/* ── Sidebar ─────────────────────────────────────────────── */
#sidebar {
    background-color: rgba(15, 23, 42, 240);
    border-right: 1px solid #1e293b;
    min-width: 220px;
    max-width: 220px;
}

#sidebar QPushButton {
    text-align: left;
    padding: 12px 16px;
    border: none;
    border-radius: 8px;
    color: #cbd5e1;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}

#sidebar QPushButton:hover {
    background-color: #1e293b;
    color: #f1f5f9;
}

#sidebar QPushButton:checked,
#sidebar QPushButton[active="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e3a5f, stop:1 #1e293b);
    color: #60a5fa;
    font-weight: 600;
    border-left: 3px solid #3b82f6;
}

#sidebarTitle {
    color: #f1f5f9;
    font-size: 18px;
    font-weight: 700;
    padding: 16px;
    background: transparent;
}

#sidebarVersion {
    color: #64748b;
    font-size: 11px;
    padding: 8px 16px;
    background: transparent;
}

/* ── Cards ───────────────────────────────────────────────── */
.card, #card {
    background-color: rgba(30, 41, 59, 180);
    border: 1px solid #334155;
    border-radius: 14px;
    padding: 20px;
}

/* ── Buttons ─────────────────────────────────────────────── */
QPushButton {
    padding: 10px 20px;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton#primaryBtn,
QPushButton[cssClass="primary"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #22c55e, stop:1 #16a34a);
    color: #022c22;
}

QPushButton#primaryBtn:hover,
QPushButton[cssClass="primary"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4ade80, stop:1 #22c55e);
}

QPushButton#dangerBtn,
QPushButton[cssClass="danger"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ef4444, stop:1 #dc2626);
    color: #fee2e2;
}

QPushButton#dangerBtn:hover,
QPushButton[cssClass="danger"]:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f87171, stop:1 #ef4444);
}

QPushButton#secondaryBtn,
QPushButton[cssClass="secondary"] {
    background-color: #1e293b;
    color: #cbd5e1;
    border: 1px solid #334155;
}

QPushButton#secondaryBtn:hover,
QPushButton[cssClass="secondary"]:hover {
    background-color: #334155;
    color: #f1f5f9;
}

QPushButton:disabled {
    background-color: #1e293b;
    color: #475569;
}

/* ── Inputs ──────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox {
    padding: 10px 14px;
    border: 1px solid #334155;
    border-radius: 8px;
    background-color: #020617;
    color: #e5e7eb;
    font-size: 13px;
    selection-background-color: #2563eb;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border-color: #3b82f6;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #94a3b8;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #e5e7eb;
    selection-background-color: #2563eb;
    padding: 4px;
}

/* ── Labels ──────────────────────────────────────────────── */
QLabel {
    background: transparent;
    color: #e5e7eb;
}

QLabel#sectionTitle {
    font-size: 22px;
    font-weight: 700;
    color: #f1f5f9;
    padding-bottom: 4px;
}

QLabel#sectionSubtitle {
    font-size: 13px;
    color: #94a3b8;
}

QLabel#heroTitle {
    font-size: 28px;
    font-weight: 700;
    color: #f1f5f9;
}

QLabel#heroSubtitle {
    font-size: 14px;
    color: #94a3b8;
}

/* ── Tables ──────────────────────────────────────────────── */
QTableWidget, QTableView {
    background-color: #0f172a;
    alternate-background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    gridline-color: #1e293b;
    selection-background-color: #1e3a5f;
    color: #e5e7eb;
}

QTableWidget::item {
    padding: 8px 12px;
}

QHeaderView::section {
    background-color: #1e293b;
    color: #94a3b8;
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid #334155;
    font-weight: 600;
    font-size: 12px;
    text-transform: uppercase;
}

/* ── Scrollbar ───────────────────────────────────────────── */
QScrollBar:vertical {
    background: #0f172a;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #0f172a;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #334155;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #475569;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Tab Bar (filter tabs) ───────────────────────────────── */
QTabBar::tab {
    background: #020617;
    border: 1px solid #334155;
    color: #cbd5e1;
    padding: 8px 18px;
    border-radius: 999px;
    margin-right: 6px;
}

QTabBar::tab:selected {
    background: #2563eb;
    border-color: #2563eb;
    color: white;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background: #1e293b;
}

/* ── GroupBox ─────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #334155;
    border-radius: 12px;
    margin-top: 14px;
    padding-top: 18px;
    font-weight: 600;
    color: #94a3b8;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 12px;
}

/* ── Splitter ────────────────────────────────────────────── */
QSplitter::handle {
    background-color: #334155;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

/* ── Status Bar ──────────────────────────────────────────── */
QStatusBar {
    background-color: #020617;
    border-top: 1px solid #1e293b;
    color: #64748b;
    font-size: 12px;
}

/* ── Tooltip ─────────────────────────────────────────────── */
QToolTip {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Dialog ──────────────────────────────────────────────── */
QDialog {
    background-color: #0f172a;
}

QMessageBox {
    background-color: #0f172a;
}

QMessageBox QPushButton {
    min-width: 80px;
}

/* ── Badge labels ────────────────────────────────────────── */
QLabel#badgeMissing {
    background-color: #7c2d12;
    color: #fed7aa;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#badgeModified {
    background-color: #1e40af;
    color: #bfdbfe;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#badgeSynced {
    background-color: #14532d;
    color: #bbf7d0;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#badgeApplied {
    background-color: #065f46;
    color: #a7f3d0;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
}

/* ── Log Panel ───────────────────────────────────────────── */
#logPanel {
    background-color: #020617;
    border: 1px solid #1e293b;
    border-radius: 10px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
    padding: 10px;
    color: #94a3b8;
}

/* ── Diff Viewer ─────────────────────────────────────────── */
#diffLeft, #diffRight {
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
    background-color: #020617;
    border: 1px solid #334155;
    border-radius: 10px;
}
"""


def apply_theme(app):
    """Apply the dark theme QSS to the QApplication."""
    app.setStyleSheet(DARK_THEME)
