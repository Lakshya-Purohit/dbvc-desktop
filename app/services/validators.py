"""
Connection string builder & validation helpers.
"""

from urllib.parse import quote_plus
from app.services.errors import AppError
from app.logger import get_logger

log = get_logger("validators")


def validate_db_type(db_type: str):
    if not db_type:
        raise AppError("Database type is required")
    if db_type not in ("postgres", "mssql"):
        raise AppError(f"Unsupported database type: {db_type}")


def build_connection_string(
    db_type: str,
    host: str,
    port: str,
    database: str,
    user: str,
    password: str,
) -> str:
    """Build a SQLAlchemy connection URL from simple form inputs."""
    validate_db_type(db_type)

    host = (host or "").strip()
    database = (database or "").strip()
    user = (user or "").strip()
    port = (port or "").strip()

    if not host or not database or not user:
        raise AppError("Host, database name, and username are required")

    if not port:
        port = "5432" if db_type == "postgres" else "1433"

    safe_password = quote_plus(password or "")

    if db_type == "postgres":
        url = f"postgresql+psycopg2://{user}:{safe_password}@{host}:{port}/{database}"
    else:
        driver = quote_plus("ODBC Driver 17 for SQL Server")
        url = (
            f"mssql+pyodbc://{user}:{safe_password}@{host},{port}/{database}"
            f"?driver={driver}"
        )

    log.debug("Built connection string for %s → %s@%s:%s/%s", db_type, user, host, port, database)
    return url
