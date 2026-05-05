"""
SQLAlchemy engine factory with detailed logging.
"""

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from app.services.errors import AppError
from app.logger import get_logger

log = get_logger("db_factory")


def get_engine(conn_string: str):
    """Create a SQLAlchemy engine and verify the connection."""
    log.info("Connecting to database...")
    log.debug("Connection string (masked): %s", _mask_password(conn_string))

    try:
        engine = create_engine(conn_string, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.close()
        log.info("Database connection successful ✓")
        return engine

    except OperationalError as e:
        error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
        log.error("Database connection FAILED: %s", error_msg)
        raise AppError(
            f"Unable to connect to the database: {error_msg}.\n"
            "Please verify:\n"
            "  • Database server is running\n"
            "  • Connection details are correct\n"
            "  • Network access is available"
        )

    except Exception as e:
        log.error("Unexpected connection error: %s", e, exc_info=True)
        raise AppError(f"Connection error: {e}")


def _mask_password(url: str) -> str:
    """Mask password in a connection URL for safe logging."""
    try:
        # postgresql+psycopg2://user:PASSWORD@host:port/db
        if "://" in url and "@" in url:
            prefix, rest = url.split("://", 1)
            if ":" in rest.split("@")[0]:
                user_pass, host_part = rest.split("@", 1)
                user = user_pass.split(":")[0]
                return f"{prefix}://{user}:****@{host_part}"
    except Exception:
        pass
    return "****"
