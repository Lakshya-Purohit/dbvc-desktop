"""Snapshot model dataclass."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Snapshot:
    """Represents a saved schema snapshot (like a git commit)."""
    id: str = ""
    connection_id: str = ""
    connection_name: str = ""
    label: str = ""
    message: str = ""
    schema_data: dict = field(default_factory=dict)
    created_at: str = ""

    @property
    def short_id(self) -> str:
        return self.id[:8] if self.id else ""

    @property
    def display_label(self) -> str:
        label = self.label or "Untitled snapshot"
        return f"{self.short_id} — {label}"

    @staticmethod
    def from_dict(d: dict) -> "Snapshot":
        return Snapshot(
            id=d.get("id", ""),
            connection_id=d.get("connection_id", ""),
            connection_name=d.get("connection_name", ""),
            label=d.get("label", ""),
            message=d.get("message", ""),
            schema_data=d.get("schema_data", {}),
            created_at=d.get("created_at", ""),
        )
