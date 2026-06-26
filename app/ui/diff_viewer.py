"""
Diff Viewer — professional side-by-side SQL diff with line numbers,
colour-coded headers, and inline change highlighting.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPlainTextEdit, QLabel,
    QSizePolicy, QFrame,
)
from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import (
    QColor, QTextCharFormat, QSyntaxHighlighter, QFont,
    QTextCursor, QPainter, QPen, QTextFormat,
)

from app.services.differ import compute_line_diffs


class SQLHighlighter(QSyntaxHighlighter):
    """SQL keyword / literal highlighter."""
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
        "PROCEDURE", "AGGREGATE", "SEQUENCE", "MATERIALIZED", "EXECUTE",
        "GRANT", "REVOKE", "WITH", "RECURSIVE", "LANGUAGE", "VOLATILE",
        "STABLE", "IMMUTABLE", "SECURITY", "DEFINER", "INVOKER",
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

        self.comment_fmt = QTextCharFormat()
        self.comment_fmt.setForeground(QColor("#64748b"))
        self.comment_fmt.setFontItalic(True)

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
        # Single-line comments
        for match in re.finditer(r'--.*$', text):
            self.setFormat(match.start(), match.end() - match.start(), self.comment_fmt)


class _LineNumberArea(QWidget):
    """Gutter that shows line numbers beside a QPlainTextEdit."""

    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint(event)


class _DiffEditor(QPlainTextEdit):
    """QPlainTextEdit subclass with a line-number gutter."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Cascadia Code", 11))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self._line_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self._update_line_area_width()
        self._real_line_numbers: list[int | None] = []

    def set_line_numbers(self, numbers: list[int | None]):
        self._real_line_numbers = numbers
        self._line_area.update()

    # ── Gutter geometry ──────────────────────────────────────────
    def line_number_area_width(self):
        max_num = max(
            (n for n in self._real_line_numbers if n is not None),
            default=1,
        )
        digits = max(3, len(str(max_num)))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_area_width(self):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_area(self, rect, dy):
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(QRect(cr.left(), cr.top(),
                                          self.line_number_area_width(), cr.height()))

    def line_number_area_paint(self, event):
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor("#0c1222"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                num = None
                if block_number < len(self._real_line_numbers):
                    num = self._real_line_numbers[block_number]
                text = str(num) if num is not None else ""
                painter.setPen(QColor("#475569"))
                painter.setFont(QFont("Cascadia Code", 10))
                painter.drawText(
                    0, top, self._line_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, text,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1
        painter.end()


class DiffViewer(QWidget):
    """Side-by-side diff viewer with line numbers and colour-coded changes."""

    COLORS = {
        "added":    QColor(22, 163, 74, 50),
        "removed":  QColor(220, 38, 38, 50),
        "modified": QColor(37, 99, 235, 45),
        "equal":    QColor(0, 0, 0, 0),
    }

    def __init__(self, source_sql="", target_sql="", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Headers ──────────────────────────────────────────────
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        left_label = QLabel("  ◀  SOURCE  (Left)")
        left_label.setObjectName("diffHeaderLeft")
        left_label.setFixedHeight(32)

        right_label = QLabel("  ▶  TARGET  (Right)")
        right_label.setObjectName("diffHeaderRight")
        right_label.setFixedHeight(32)

        header_layout.addWidget(left_label)
        header_layout.addWidget(right_label)
        layout.addLayout(header_layout)

        # ── Editors ──────────────────────────────────────────────
        editor_layout = QHBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(2)

        self.left_editor = _DiffEditor()
        self.left_editor.setObjectName("diffLeft")

        self.right_editor = _DiffEditor()
        self.right_editor.setObjectName("diffRight")

        # Sync scrolling (both axes)
        self.left_editor.verticalScrollBar().valueChanged.connect(
            self.right_editor.verticalScrollBar().setValue)
        self.right_editor.verticalScrollBar().valueChanged.connect(
            self.left_editor.verticalScrollBar().setValue)
        self.left_editor.horizontalScrollBar().valueChanged.connect(
            self.right_editor.horizontalScrollBar().setValue)
        self.right_editor.horizontalScrollBar().valueChanged.connect(
            self.left_editor.horizontalScrollBar().setValue)

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
        left_nums: list[int | None] = []
        right_nums: list[int | None] = []

        for ld in line_diffs:
            left_text.append(ld["left_line"] or "")
            right_text.append(ld["right_line"] or "")
            left_colors.append(ld["status"])
            right_colors.append(ld["status"])
            left_nums.append(ld["left_num"])
            right_nums.append(ld["right_num"])

        self.left_editor.setPlainText("\n".join(left_text))
        self.right_editor.setPlainText("\n".join(right_text))

        self.left_editor.set_line_numbers(left_nums)
        self.right_editor.set_line_numbers(right_nums)

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
