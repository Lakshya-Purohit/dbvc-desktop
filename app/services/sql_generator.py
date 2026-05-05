"""
CREATE TABLE SQL generation from column definitions.
"""

import re
from app.logger import get_logger

log = get_logger("sql_generator")


def generate_create_table_sql(table_name: str, columns: list[dict], schema: str = "app") -> str:
    """Generate a CREATE TABLE statement from column metadata."""
    col_defs = []

    for col in columns:
        col_name = col["name"]
        col_type = col["type"]
        default = col["default"]

        # Detect SERIAL-like columns
        is_sequence = (
            default is not None
            and isinstance(default, str)
            and "nextval" in default
        )

        if is_sequence:
            line = f"{col_name} SERIAL"
        else:
            line = f"{col_name} {col_type}"
            if not col["nullable"]:
                line += " NOT NULL"
            if default:
                line += f" DEFAULT {default}"

        col_defs.append(line)

    cols_sql = ",\n    ".join(col_defs)

    sql = f"""
CREATE SCHEMA IF NOT EXISTS {schema};

CREATE TABLE IF NOT EXISTS {schema}.{table_name} (
    {cols_sql}
);
""".strip()

    log.debug("Generated CREATE TABLE for %s.%s (%d columns)", schema, table_name, len(columns))
    return sql


def generate_schema_sql(schema: str = "app") -> str:
    return f"CREATE SCHEMA IF NOT EXISTS {schema};"
