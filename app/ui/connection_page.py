"""
Connection Page — manage database connection profiles.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
    QLineEdit, QComboBox, QMessageBox, QHeaderView,
)
from PyQt6.QtCore import Qt
from app.services.snapshot_store import SnapshotStore
from app.services.validators import build_connection_string
from app.services.db_factory import get_engine
from app.services.errors import AppError
from app.logger import get_logger

log = get_logger("connections")


class ConnectionDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Connection" if data else "New Connection")
        self.setMinimumWidth(450)
        self.data = data or {}
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_input = QLineEdit(self.data.get("name", ""))
        self.name_input.setPlaceholderText("e.g. Production DB")
        form.addRow("Profile Name:", self.name_input)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["postgres", "mssql"])
        if self.data.get("db_type"):
            self.type_combo.setCurrentText(self.data["db_type"])
        form.addRow("Database Type:", self.type_combo)
        self.host_input = QLineEdit(self.data.get("host", ""))
        self.host_input.setPlaceholderText("127.0.0.1")
        form.addRow("Host / IP:", self.host_input)
        self.port_input = QLineEdit(self.data.get("port", ""))
        self.port_input.setPlaceholderText("5432 or 1433")
        form.addRow("Port:", self.port_input)
        self.db_input = QLineEdit(self.data.get("database_name", ""))
        self.db_input.setPlaceholderText("my_database")
        form.addRow("Database Name:", self.db_input)
        self.user_input = QLineEdit(self.data.get("username", ""))
        self.user_input.setPlaceholderText("db_user")
        form.addRow("Username:", self.user_input)
        self.pass_input = QLineEdit(self.data.get("password_encrypted", ""))
        self.pass_input.setPlaceholderText("password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self.pass_input)
        layout.addLayout(form)
        btn_layout = QHBoxLayout()
        test_btn = QPushButton("🔌 Test Connection")
        test_btn.setProperty("cssClass", "secondary")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.clicked.connect(self._test)
        btn_layout.addWidget(test_btn)
        btn_layout.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setProperty("cssClass", "secondary")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        save_btn = QPushButton("💾 Save")
        save_btn.setProperty("cssClass", "primary")
        save_btn.clicked.connect(self.accept)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _test(self):
        try:
            cs = build_connection_string(
                self.type_combo.currentText(), self.host_input.text(),
                self.port_input.text(), self.db_input.text(),
                self.user_input.text(), self.pass_input.text())
            engine = get_engine(cs)
            engine.dispose()
            QMessageBox.information(self, "Success", "✅ Connection successful!")
        except AppError as e:
            QMessageBox.critical(self, "Failed", f"❌ {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def get_values(self):
        return {
            "name": self.name_input.text().strip(),
            "db_type": self.type_combo.currentText(),
            "host": self.host_input.text().strip(),
            "port": self.port_input.text().strip(),
            "database_name": self.db_input.text().strip(),
            "username": self.user_input.text().strip(),
            "password_encrypted": self.pass_input.text(),
        }


class ConnectionPage(QWidget):
    def __init__(self, store: SnapshotStore):
        super().__init__()
        self.store = store
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(16)
        title = QLabel("Database Connections")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        subtitle = QLabel("Manage your database connection profiles. Stored locally.")
        subtitle.setObjectName("sectionSubtitle")
        layout.addWidget(subtitle)
        toolbar = QHBoxLayout()
        add_btn = QPushButton("➕ New Connection")
        add_btn.setProperty("cssClass", "primary")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._add)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setProperty("cssClass", "secondary")
        refresh_btn.clicked.connect(self.refresh)
        toolbar.addWidget(refresh_btn)
        layout.addLayout(toolbar)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Name", "Type", "Host", "Port", "Database", "Actions"])
        self.table.setColumnWidth(5, 180)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        conns = self.store.get_connections()
        self.table.setRowCount(len(conns))
        for row, c in enumerate(conns):
            self.table.setItem(row, 0, QTableWidgetItem(c["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(c["db_type"]))
            self.table.setItem(row, 2, QTableWidgetItem(c["host"]))
            self.table.setItem(row, 3, QTableWidgetItem(c["port"] or "—"))
            self.table.setItem(row, 4, QTableWidgetItem(c["database_name"]))
            actions = QWidget()
            al = QHBoxLayout(actions)
            al.setContentsMargins(4, 2, 4, 2)
            al.setSpacing(6)
            edit_btn = QPushButton("✏️")
            edit_btn.setFixedSize(36, 30)
            edit_btn.clicked.connect(lambda _, cc=c: self._edit(cc))
            test_btn = QPushButton("🔌")
            test_btn.setFixedSize(36, 30)
            test_btn.clicked.connect(lambda _, cc=c: self._test(cc))
            del_btn = QPushButton("🗑️")
            del_btn.setFixedSize(36, 30)
            del_btn.setProperty("cssClass", "danger")
            del_btn.clicked.connect(lambda _, cc=c: self._delete(cc))
            al.addWidget(edit_btn)
            al.addWidget(test_btn)
            al.addWidget(del_btn)
            self.table.setCellWidget(row, 5, actions)

    def _add(self):
        d = ConnectionDialog(self)
        if d.exec() == QDialog.DialogCode.Accepted:
            v = d.get_values()
            if not v["name"]:
                QMessageBox.warning(self, "Validation", "Name is required.")
                return
            try:
                self.store.save_connection(**v)
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _edit(self, conn):
        d = ConnectionDialog(self, data=conn)
        if d.exec() == QDialog.DialogCode.Accepted:
            v = d.get_values()
            try:
                self.store.save_connection(**v, conn_id=conn["id"])
                self.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _delete(self, conn):
        r = QMessageBox.question(self, "Delete", f"Delete '{conn['name']}' and all snapshots?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.store.delete_connection(conn["id"])
            self.refresh()

    def _test(self, conn):
        try:
            cs = build_connection_string(conn["db_type"], conn["host"], conn["port"],
                conn["database_name"], conn["username"], conn["password_encrypted"])
            engine = get_engine(cs)
            engine.dispose()
            QMessageBox.information(self, "Success", f"✅ '{conn['name']}' connected!")
        except AppError as e:
            QMessageBox.critical(self, "Failed", f"❌ {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
