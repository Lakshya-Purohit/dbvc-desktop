"""
Schema introspection — fetches tables, functions, procedures, aggregates,
views, materialized views, triggers, and sequences.
Supports PostgreSQL and SQL Server with detailed logging.
Dynamically discovers all user-created schemas.
"""

from sqlalchemy import text
from app.services.errors import AppError
from app.logger import get_logger

log = get_logger("introspection")

# Canonical ordering used across the app for diffs / apply operations.
# New object categories MUST be added here so compare & apply pick them up.
OBJECT_TYPES = (
    "functions",
    "procedures",
    "aggregates",
    "views",
    "materialized_views",
    "triggers",
    "sequences",
)


def _get_user_schemas_pg(conn) -> str:
    """Return a quoted, comma-separated list of user schemas for Postgres."""
    result = conn.execute(text("""
        SELECT nspname FROM pg_namespace
        WHERE nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
        AND nspname NOT LIKE 'pg_%'
    """))
    schemas = [row[0] for row in result]
    if not schemas:
        schemas = ["public"]
    log.debug("Discovered user schemas: %s", schemas)
    return ", ".join(f"'{s}'" for s in schemas)


def fetch_objects(engine, db_type: str) -> dict:
    """Fetch functions, procedures, aggregates, views, materialized views,
    triggers, and sequences from the database."""
    log.info("Introspecting database objects (type=%s)...", db_type)

    try:
        objects = {}

        with engine.connect() as conn:
            if db_type == "postgres":
                schemas = _get_user_schemas_pg(conn)

                queries = {
                    # ── Normal functions (prokind 'f') ───────────────
                    "functions": f"""
                        SELECT proname, pg_get_functiondef(p.oid)
                        FROM pg_proc p
                        JOIN pg_namespace n ON n.oid = p.pronamespace
                        WHERE n.nspname IN ({schemas})
                        AND p.prokind = 'f'
                    """,
                    # ── Procedures (prokind 'p', PG 11+) ─────────────
                    "procedures": f"""
                        SELECT proname, pg_get_functiondef(p.oid)
                        FROM pg_proc p
                        JOIN pg_namespace n ON n.oid = p.pronamespace
                        WHERE n.nspname IN ({schemas})
                        AND p.prokind = 'p'
                    """,
                    # ── Aggregate functions (prokind 'a') ────────────
                    # pg_get_functiondef does NOT work on aggregates;
                    # reconstruct a useful definition from pg_aggregate.
                    "aggregates": f"""
                        SELECT p.proname,
                               format(
                                   'CREATE AGGREGATE %I.%I (%s) (SFUNC = %s, STYPE = %s%s)',
                                   n.nspname,
                                   p.proname,
                                   pg_get_function_identity_arguments(p.oid),
                                   a.aggtransfn::regproc,
                                   a.aggtranstype::regtype,
                                   CASE WHEN a.aggfinalfn != 0
                                        THEN ', FINALFUNC = ' || a.aggfinalfn::regproc::text
                                        ELSE '' END
                               )
                        FROM pg_proc p
                        JOIN pg_namespace n ON n.oid = p.pronamespace
                        JOIN pg_aggregate a ON a.aggfnoid = p.oid
                        WHERE n.nspname IN ({schemas})
                        AND p.prokind = 'a'
                    """,
                    # ── Regular views ────────────────────────────────
                    "views": f"""
                        SELECT table_name, view_definition
                        FROM information_schema.views
                        WHERE table_schema IN ({schemas})
                    """,
                    # ── Materialized views ───────────────────────────
                    "materialized_views": f"""
                        SELECT c.relname,
                               pg_get_viewdef(c.oid, true)
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE c.relkind = 'm'
                        AND n.nspname IN ({schemas})
                    """,
                    # ── Triggers ─────────────────────────────────────
                    "triggers": f"""
                        SELECT tgname, pg_get_triggerdef(t.oid)
                        FROM pg_trigger t
                        JOIN pg_class c ON c.oid = t.tgrelid
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE NOT t.tgisinternal
                        AND n.nspname IN ({schemas})
                    """,
                    # ── Sequences ────────────────────────────────────
                    "sequences": f"""
                        SELECT s.sequence_name,
                               'CREATE SEQUENCE ' || s.sequence_schema || '.' || s.sequence_name
                               || ' AS ' || s.data_type
                               || ' INCREMENT BY ' || s.increment
                               || ' MINVALUE ' || s.minimum_value
                               || ' MAXVALUE ' || s.maximum_value
                               || ' START WITH ' || s.start_value
                               || CASE WHEN s.cycle_option = 'YES' THEN ' CYCLE' ELSE ' NO CYCLE' END
                        FROM information_schema.sequences s
                        WHERE s.sequence_schema IN ({schemas})
                    """,
                }
            elif db_type == "mssql":
                queries = {
                    "functions": """
                        SELECT o.name, m.definition
                        FROM sys.sql_modules m
                        JOIN sys.objects o ON m.object_id = o.object_id
                        WHERE o.type IN ('FN', 'IF', 'TF')
                        AND SCHEMA_NAME(o.schema_id) NOT IN ('sys', 'INFORMATION_SCHEMA')
                    """,
                    "procedures": """
                        SELECT o.name, m.definition
                        FROM sys.sql_modules m
                        JOIN sys.objects o ON m.object_id = o.object_id
                        WHERE o.type = 'P'
                        AND SCHEMA_NAME(o.schema_id) NOT IN ('sys', 'INFORMATION_SCHEMA')
                    """,
                    "aggregates": """
                        SELECT name,
                               'CREATE AGGREGATE ' + SCHEMA_NAME(schema_id) + '.' + name
                        FROM sys.objects
                        WHERE type = 'AF'
                        AND SCHEMA_NAME(schema_id) NOT IN ('sys', 'INFORMATION_SCHEMA')
                    """,
                    "views": """
                        SELECT o.name, m.definition
                        FROM sys.sql_modules m
                        JOIN sys.objects o ON m.object_id = o.object_id
                        WHERE o.type = 'V'
                        AND SCHEMA_NAME(o.schema_id) NOT IN ('sys', 'INFORMATION_SCHEMA')
                    """,
                    "materialized_views": """
                        SELECT o.name, m.definition
                        FROM sys.sql_modules m
                        JOIN sys.objects o ON m.object_id = o.object_id
                        JOIN sys.indexes i ON o.object_id = i.object_id AND i.index_id = 1
                        WHERE o.type = 'V'
                        AND SCHEMA_NAME(o.schema_id) NOT IN ('sys', 'INFORMATION_SCHEMA')
                    """,
                    "triggers": """
                        SELECT o.name, m.definition
                        FROM sys.sql_modules m
                        JOIN sys.objects o ON m.object_id = o.object_id
                        WHERE o.type = 'TR'
                        AND SCHEMA_NAME(o.schema_id) NOT IN ('sys', 'INFORMATION_SCHEMA')
                    """,
                    "sequences": """
                        SELECT name,
                               'CREATE SEQUENCE ' + SCHEMA_NAME(schema_id) + '.' + name
                               + ' AS ' + TYPE_NAME(system_type_id)
                               + ' START WITH ' + CAST(start_value AS VARCHAR)
                               + ' INCREMENT BY ' + CAST(increment AS VARCHAR)
                               + ' MINVALUE ' + CAST(minimum_value AS VARCHAR)
                               + ' MAXVALUE ' + CAST(maximum_value AS VARCHAR)
                               + CASE WHEN is_cycling = 1 THEN ' CYCLE' ELSE ' NO CYCLE' END
                        FROM sys.sequences
                        WHERE SCHEMA_NAME(schema_id) NOT IN ('sys', 'INFORMATION_SCHEMA')
                    """,
                }
            else:
                raise AppError("Unsupported database type for object introspection")

            for obj_type, sql in queries.items():
                log.debug("Fetching %s...", obj_type)
                try:
                    result = conn.execute(text(sql))
                    items = {row[0]: row[1] for row in result}
                    objects[obj_type] = items
                    log.info("  → %s: %d objects found", obj_type, len(items))
                except Exception as e:
                    # Log but don't abort the entire introspection for one
                    # failing category (e.g. PG < 11 has no prokind='p').
                    log.warning("  → %s: skipped (%s)", obj_type, e)
                    objects[obj_type] = {}

        total = sum(len(v) for v in objects.values())
        log.info("Introspection complete: %d total objects", total)
        return objects

    except AppError:
        raise
    except Exception as e:
        log.error("Failed to introspect database objects: %s", e, exc_info=True)
        raise AppError(f"Failed to read database objects: {e}")


def fetch_tables(engine, db_type: str = "postgres") -> dict:
    """Fetch table column definitions from all user schemas."""
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
        WHERE SCHEMA_NAME(t.schema_id) NOT IN ('sys', 'INFORMATION_SCHEMA')
        ORDER BY t.name, c.column_id;
        """
    elif db_type == "postgres":
        # Dynamically discover user schemas for table introspection too.
        try:
            with engine.connect() as conn:
                schemas = _get_user_schemas_pg(conn)
        except Exception:
            schemas = "'public'"

        sql = f"""
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema IN ({schemas})
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
