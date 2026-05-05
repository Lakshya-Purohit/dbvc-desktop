"""
SQL executor — applies SQL to a target database with safety checks.
"""

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.services.errors import AppError
from app.logger import get_logger

log = get_logger("executor")

FORBIDDEN = ["DROP DATABASE", "DROP SCHEMA"]


def apply_sql(engine, sql: str, obj_type: str = "") -> None:
    """Execute SQL against the target database."""
    upper = sql.upper()

    for word in FORBIDDEN:
        if word in upper:
            log.warning("BLOCKED forbidden operation: %s", word)
            raise AppError("Forbidden operation detected — DROP DATABASE / DROP SCHEMA are not allowed")

    log.info("Applying %s SQL (%d chars)...", obj_type or "unknown", len(sql))
    log.debug("SQL preview: %s", sql[:200])

    try:
        with engine.begin() as conn:
            conn.execute(text(sql))
        log.info("SQL applied successfully ✓")

    except ProgrammingError as e:
        msg = str(e.orig).lower()
        log.error("SQL execution error: %s", e.orig)

        if obj_type == "tables":
            raise AppError(
                "Failed to apply table. Check definition or permissions."
            )

        if "does not exist" in msg:
            raise AppError(
                "Cannot apply — required dependencies do not exist yet. "
                "Apply base objects first (tables → functions → views → triggers)."
            )

        raise AppError(f"Failed to apply database object: {e.orig}")

    except Exception as e:
        log.error("Unexpected SQL execution error: %s", e, exc_info=True)
        raise AppError(f"SQL execution error: {e}")
