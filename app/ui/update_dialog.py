"""
Update Notification Dialog — premium popup shown when a new version
is available on GitHub Releases.
"""

import webbrowser

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QCheckBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from app.config import APP_VERSION


class UpdateDialog(QDialog):
    """
    A polished, non-blocking dialog that informs the user about a
    new version and offers a direct link to the release page.
    """

    def __init__(self, version: str, release_url: str, release_notes: str, parent=None):
        super().__init__(parent)
        self.release_url = release_url
        self.setWindowTitle("Update Available")
        self.setFixedWidth(520)
        self.setMinimumHeight(300)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(16)

        # ── Icon + Title ─────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_label = QLabel("🚀")
        icon_label.setFont(QFont("Segoe UI Emoji", 32))
        icon_label.setFixedSize(56, 56)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:1, "
            "stop:0 rgba(37, 99, 235, 60), stop:1 rgba(99, 102, 241, 60));"
            "border-radius: 14px;"
        )
        header.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("A New Version is Available!")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #f1f5f9;")
        title_col.addWidget(title)

        version_label = QLabel(f"v{APP_VERSION}  →  {version}")
        version_label.setStyleSheet("color: #60a5fa; font-size: 13px; font-weight: 600;")
        title_col.addWidget(version_label)

        header.addLayout(title_col)
        header.addStretch()
        layout.addLayout(header)

        # ── Divider ──────────────────────────────────────────────
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background-color: #1e293b;")
        layout.addWidget(divider)

        # ── Description ─────────────────────────────────────────
        desc = QLabel(
            "A newer version of <b>DBVC Desktop</b> has been published. "
            "We recommend updating to get the latest features, bug fixes, "
            "and security improvements."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.5;")
        desc.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(desc)

        # ── Release Notes (if available) ─────────────────────────
        if release_notes.strip():
            notes_frame = QFrame()
            notes_frame.setStyleSheet(
                "background-color: #020617; border: 1px solid #1e293b; "
                "border-radius: 10px; padding: 12px;"
            )
            nf_layout = QVBoxLayout(notes_frame)
            nf_layout.setContentsMargins(12, 8, 12, 8)

            notes_title = QLabel("📋 What's New")
            notes_title.setStyleSheet("color: #e2e8f0; font-weight: 600; font-size: 12px;")
            nf_layout.addWidget(notes_title)

            notes_text = QLabel(release_notes)
            notes_text.setWordWrap(True)
            notes_text.setStyleSheet("color: #94a3b8; font-size: 12px;")
            notes_text.setMaximumHeight(120)
            nf_layout.addWidget(notes_text)

            layout.addWidget(notes_frame)

        layout.addStretch()

        # ── Buttons ──────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        later_btn = QPushButton("Remind Me Later")
        later_btn.setProperty("cssClass", "secondary")
        later_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        later_btn.setMinimumWidth(140)
        later_btn.clicked.connect(self.reject)
        btn_layout.addWidget(later_btn)

        btn_layout.addStretch()

        download_btn = QPushButton("⬇  Download Update")
        download_btn.setProperty("cssClass", "primary")
        download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        download_btn.setMinimumWidth(180)
        download_btn.setMinimumHeight(38)
        download_btn.clicked.connect(self._open_release)
        btn_layout.addWidget(download_btn)

        layout.addLayout(btn_layout)

    def _open_release(self):
        """Open the GitHub release page in the default browser."""
        webbrowser.open(self.release_url)
        self.accept()
