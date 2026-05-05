"""
Schema introspection — fetches tables, functions, views, triggers.
Supports PostgreSQL and SQL Server with detailed logging.
"""

from sqlalchemy import text
from app.services.errors import AppError
from app.logger import get_logger

log = get_logger("introspection")


def fetch_objects(engine, db_type: str) -> dict:
    """Fetch functions, views, and triggers from the database."""
    log.info("Introspecting database objects (type=%s)...", db_type)

    try:
        objects = {}

        with engine.connect() as conn:
            if db_type == "postgres":
                queries = {
                    "functions": """
                        SELECT proname, pg_get_functiondef(p.oid)
                        FROM pg_proc p
                        JOIN pg_namespace n ON n.oid = p.pronamespace
                        WHERE n.nspname IN ('public', 'app')
                    """,
                    "views": """
                        SELECT table_name, view_definition
                        FROM information_schema.views
                        WHERE table_schema IN ('public', 'app')
                    """,
                    "triggers": """
                        SELECT tgname, pg_get_triggerdef(t.oid)
                        FROM pg_trigger t
                        JOIN pg_class c ON c.oid = t.tgrelid
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE NOT t.tgisinternal
                        AND n.nspname IN ('public', 'app')
                    """,
                }
            elif db_type == "mssql":
                queries = {
                    "functions": """
                        SELECT o.name, m.definition
                        FROM sys.sql_modules m
                        JOIN sys.objects o ON m.object_id = o.object_id
                        WHERE o.type IN ('P', 'FN', 'IF', 'TF')
                        AND SCHEMA_NAME(o.schema_id) = 'dbo'
                    """,
                    "views": """
                        SELECT o.name, m.definition
                        FROM sys.sql_modules m
                        JOIN sys.objects o ON m.object_id = o.object_id
                        WHERE o.type = 'V'
                        AND SCHEMA_NAME(o.schema_id) = 'dbo'
                    """,
                    "triggers": """
                        SELECT o.name, m.definition
                        FROM sys.sql_modules m
                        JOIN sys.objects o ON m.object_id = o.object_id
                        WHERE o.type = 'TR'
                        AND SCHEMA_NAME(o.schema_id) = 'dbo'
                    """,
                }
            else:
                raise AppError("Unsupported database type for object introspection")

            for obj_type, sql in queries.items():
                log.debug("Fetching %s...", obj_type)
                result = conn.execute(text(sql))
                items = {row[0]: row[1] for row in result}
                objects[obj_type] = items
                log.info("  → %s: %d objects found", obj_type, len(items))

        total = sum(len(v) for v in objects.values())
        log.info("Introspection complete: %d total objects", total)
        return objects

    except AppError:
        raise
    except Exception as e:
        log.error("Failed to introspect database objects: %s", e, exc_info=True)
        raise AppError(f"Failed to read database objects: {e}")


def fetch_tables(engine, db_type: str = "postgres") -> dict:
    """Fetch table column definitions."""
    log.info("Introspecting tables (type=%s)...", db_type)

    if db_type == "mssql":
        sql = """
        SELECT
            t.name AS table_name,
            c.name AS column_name,
            ty.name AS data_type,
            CASE WHEN c.is_nullable = 1 THEN 'YES' ELSE 'NO' END AS is_nullable,
            OBJECT_DEFINITION(c.default_object_id) AS column_default
        FROM sys.tables t
        JOIN sys.columns c ON t.object_id = c.object_id
        JOIN sys.types ty ON c.user_type_id = ty.user_type_id
        WHERE SCHEMA_NAME(t.schema_id) = 'dbo'
        ORDER BY t.name, c.column_id;
        """
    elif db_type == "postgres":
        sql = """
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema IN ('public', 'app')
        ORDER BY table_name, ordinal_position;
        """
    else:
        raise AppError("Unsupported database type for table introspection")

    tables = {}

    try:
        with engine.connect() as conn:
            for row in conn.execute(text(sql)):
                table = row.table_name
                tables.setdefault(table, []).append(
                    {
                        "name": row.column_name,
                        "type": row.data_type,
                        "nullable": str(row.is_nullable).upper() in ("YES", "Y", "TRUE", "1"),
                        "default": row.column_default,
                    }
                )

        log.info("Tables introspected: %d tables found", len(tables))
        for t_name, cols in tables.items():
            log.debug("  → %s: %d columns", t_name, len(cols))

        return tables

    except AppError:
        raise
    except Exception as e:
        log.error("Failed to introspect tables: %s", e, exc_info=True)
        raise AppError(f"Failed to read tables: {e}")
