"""Connection profile dataclass."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConnectionProfile:
    """Represents a saved database connection."""
    id: str = ""
    name: str = ""
    db_type: str = "postgres"   # "postgres" or "mssql"
    host: str = ""
    port: str = ""
    database_name: str = ""
    username: str = ""
    password_encrypted: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def display_label(self) -> str:
        return f"{self.name} ({self.db_type} — {self.host}:{self.port}/{self.database_name})"

    @staticmethod
    def from_dict(d: dict) -> "ConnectionProfile":
        return ConnectionProfile(
            id=d.get("id", ""),
            name=d.get("name", ""),
            db_type=d.get("db_type", "postgres"),
            host=d.get("host", ""),
            port=d.get("port", ""),
            database_name=d.get("database_name", ""),
            username=d.get("username", ""),
            password_encrypted=d.get("password_encrypted", ""),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )
