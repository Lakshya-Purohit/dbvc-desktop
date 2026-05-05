"""
Diff Viewer — side-by-side syntax-highlighted SQL diff widget.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPlainTextEdit, QLabel,
    QScrollBar, QSizePolicy,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QSyntaxHighlighter, QFont, QTextCursor

from app.services.differ import compute_line_diffs


class SQLHighlighter(QSyntaxHighlighter):
    """Basic SQL keyword highlighter."""
    KEYWORDS = [
        "SELECT", "FROM", "WHERE", "INSERT", "UPDATE", "DELETE", "CREATE",
        "ALTER", "DROP", "TABLE", "VIEW", "FUNCTION", "TRIGGER", "INDEX",
        "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "NOT", "NULL", "DEFAULT",
        "AND", "OR", "IN", "EXISTS", "JOIN", "LEFT", "RIGHT", "INNER",
        "OUTER", "ON", "AS", "SET", "VALUES", "INTO", "IF", "ELSE",
        "BEGIN", "END", "RETURN", "RETURNS", "DECLARE", "SCHEMA", "SERIAL",
        "INTEGER", "VARCHAR", "TEXT", "BOOLEAN", "TIMESTAMP", "DECIMAL",
        "UNIQUE", "CASCADE", "REPLACE", "CONSTRAINT", "ORDER", "BY",
        "GROUP", "HAVING", "LIMIT", "OFFSET", "UNION", "ALL", "DISTINCT",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.keyword_fmt = QTextCharFormat()
        self.keyword_fmt.setForeground(QColor("#60a5fa"))
        self.keyword_fmt.setFontWeight(QFont.Weight.Bold)

        self.string_fmt = QTextCharFormat()
        self.string_fmt.setForeground(QColor("#fbbf24"))

        self.number_fmt = QTextCharFormat()
        self.number_fmt.setForeground(QColor("#a78bfa"))

    def highlightBlock(self, text):
        import re
        # Keywords
        for kw in self.KEYWORDS:
            pattern = rf'\b{kw}\b'
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(match.start(), match.end() - match.start(), self.keyword_fmt)
        # Strings
        for match in re.finditer(r"'[^']*'", text):
            self.setFormat(match.start(), match.end() - match.start(), self.string_fmt)
        # Numbers
        for match in re.finditer(r'\b\d+\b', text):
            self.setFormat(match.start(), match.end() - match.start(), self.number_fmt)


class DiffViewer(QWidget):
    """Side-by-side diff viewer with line-by-line coloring."""

    COLORS = {
        "added": QColor(22, 163, 74, 40),
        "removed": QColor(220, 38, 38, 40),
        "modified": QColor(37, 99, 235, 40),
        "equal": QColor(0, 0, 0, 0),
    }

    def __init__(self, source_sql="", target_sql="", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Headers
        header_layout = QHBoxLayout()
        left_label = QLabel("  📄 Source (Left)")
        left_label.setStyleSheet("font-weight:600; color:#94a3b8; padding:8px; background:#0f172a; border-bottom:1px solid #1e293b;")
        right_label = QLabel("  📄 Target (Right)")
        right_label.setStyleSheet("font-weight:600; color:#94a3b8; padding:8px; background:#0f172a; border-bottom:1px solid #1e293b;")
        header_layout.addWidget(left_label)
        header_layout.addWidget(right_label)
        header_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header_layout)

        # Editors
        editor_layout = QHBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(2)

        self.left_editor = QPlainTextEdit()
        self.left_editor.setObjectName("diffLeft")
        self.left_editor.setReadOnly(True)
        self.left_editor.setFont(QFont("Cascadia Code", 11))
        self.left_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.right_editor = QPlainTextEdit()
        self.right_editor.setObjectName("diffRight")
        self.right_editor.setReadOnly(True)
        self.right_editor.setFont(QFont("Cascadia Code", 11))
        self.right_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        # Sync scrolling
        self.left_editor.verticalScrollBar().valueChanged.connect(
            self.right_editor.verticalScrollBar().setValue)
        self.right_editor.verticalScrollBar().valueChanged.connect(
            self.left_editor.verticalScrollBar().setValue)

        # SQL highlighting
        self.left_hl = SQLHighlighter(self.left_editor.document())
        self.right_hl = SQLHighlighter(self.right_editor.document())

        editor_layout.addWidget(self.left_editor)
        editor_layout.addWidget(self.right_editor)
        layout.addLayout(editor_layout)

        if source_sql or target_sql:
            self.set_diff(source_sql, target_sql)

    def set_diff(self, source_sql: str, target_sql: str):
        """Populate the diff viewer with source and target SQL."""
        source_lines = source_sql.splitlines() if source_sql else []
        target_lines = target_sql.splitlines() if target_sql else []
        line_diffs = compute_line_diffs(source_lines, target_lines)

        left_text = []
        right_text = []
        left_colors = []
        right_colors = []

        for ld in line_diffs:
            left_text.append(ld["left_line"] or "")
            right_text.append(ld["right_line"] or "")
            status = ld["status"]
            left_colors.append(status)
            right_colors.append(status)

        self.left_editor.setPlainText("\n".join(left_text))
        self.right_editor.setPlainText("\n".join(right_text))

        # Apply background colors
        self._colorize(self.left_editor, left_colors, "left")
        self._colorize(self.right_editor, right_colors, "right")

    def _colorize(self, editor, colors, side):
        cursor = editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        for i, status in enumerate(colors):
            cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)

            fmt = QTextCharFormat()
            if status == "removed" and side == "left":
                fmt.setBackground(self.COLORS["removed"])
            elif status == "added" and side == "right":
                fmt.setBackground(self.COLORS["added"])
            elif status == "modified":
                fmt.setBackground(self.COLORS["modified"])

            cursor.mergeCharFormat(fmt)

            if i < len(colors) - 1:
                cursor.movePosition(QTextCursor.MoveOperation.NextBlock)
