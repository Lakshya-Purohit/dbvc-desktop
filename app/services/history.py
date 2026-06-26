"""
Version history — compare snapshots, build timelines.
"""

import json
from typing import Optional

from app.services.snapshot_store import SnapshotStore
from app.services.normalizer import normalize
from app.services.sql_generator import generate_create_table_sql
from app.services.introspection import OBJECT_TYPES
from app.logger import get_logger

log = get_logger("history")


def get_timeline(store: SnapshotStore, connection_id: Optional[str] = None) -> list[dict]:
    """Get a chronological list of snapshots (newest first)."""
    snapshots = store.get_snapshots(connection_id)
    log.info("Timeline loaded: %d snapshots", len(snapshots))
    return snapshots


def compare_snapshots(store: SnapshotStore, snap_id_1: str, snap_id_2: str) -> list[dict]:
    """
    Compare two snapshots and return a list of diff items.
    Same structure as the web app's compare route output.
    """
    log.info("Comparing snapshots: %s ↔ %s", snap_id_1[:8], snap_id_2[:8])

    snap1 = store.get_snapshot(snap_id_1)
    snap2 = store.get_snapshot(snap_id_2)

    if not snap1 or not snap2:
        log.error("One or both snapshots not found")
        return []

    schema1 = snap1["schema_data"]
    schema2 = snap2["schema_data"]

    diffs = []

    # ── Table diffs ──────────────────────────────────────────────────
    tables1 = schema1.get("tables", {})
    tables2 = schema2.get("tables", {})

    for table_name in set(tables1.keys()) | set(tables2.keys()):
        if table_name in tables1 and table_name not in tables2:
            diffs.append({
                "type": "tables",
                "name": table_name,
                "status": "missing_in_target",
                "source_sql": generate_create_table_sql(table_name, tables1[table_name]),
                "target_sql": "",
            })
        elif table_name in tables2 and table_name not in tables1:
            diffs.append({
                "type": "tables",
                "name": table_name,
                "status": "missing_in_source",
                "source_sql": "",
                "target_sql": generate_create_table_sql(table_name, tables2[table_name]),
            })
        else:
            sql1 = generate_create_table_sql(table_name, tables1[table_name])
            sql2 = generate_create_table_sql(table_name, tables2[table_name])
            if sql1 != sql2:
                diffs.append({
                    "type": "tables",
                    "name": table_name,
                    "status": "modified",
                    "source_sql": sql1,
                    "target_sql": sql2,
                })

    # ── Object diffs (all tracked object types) ───────────────────────
    for obj_type in OBJECT_TYPES:
        objs1 = schema1.get(obj_type, {})
        objs2 = schema2.get(obj_type, {})

        for name in set(objs1.keys()) | set(objs2.keys()):
            if name in objs1 and name not in objs2:
                diffs.append({
                    "type": obj_type,
                    "name": name,
                    "status": "missing_in_target",
                    "source_sql": normalize(objs1[name]),
                    "target_sql": "",
                })
            elif name in objs2 and name not in objs1:
                diffs.append({
                    "type": obj_type,
                    "name": name,
                    "status": "missing_in_source",
                    "source_sql": "",
                    "target_sql": normalize(objs2[name]),
                })
            else:
                sql1 = normalize(objs1[name])
                sql2 = normalize(objs2[name])
                if sql1 != sql2:
                    diffs.append({
                        "type": obj_type,
                        "name": name,
                        "status": "modified",
                        "source_sql": sql1,
                        "target_sql": sql2,
                    })

    log.info("Comparison complete: %d differences found", len(diffs))
    return diffs


def compare_live_vs_snapshot(
    store: SnapshotStore,
    snap_id: str,
    live_tables: dict,
    live_objects: dict,
) -> list[dict]:
    """Compare a live database schema against a saved snapshot."""
    log.info("Comparing live DB ↔ snapshot %s", snap_id[:8])

    snap = store.get_snapshot(snap_id)
    if not snap:
        log.error("Snapshot not found: %s", snap_id)
        return []

    schema = snap["schema_data"]
    diffs = []

    # Tables
    snap_tables = schema.get("tables", {})
    for table_name in set(live_tables.keys()) | set(snap_tables.keys()):
        if table_name in live_tables and table_name not in snap_tables:
            diffs.append({
                "type": "tables",
                "name": table_name,
                "status": "missing_in_target",
                "source_sql": generate_create_table_sql(table_name, live_tables[table_name]),
                "target_sql": "",
            })
        elif table_name in snap_tables and table_name not in live_tables:
            diffs.append({
                "type": "tables",
                "name": table_name,
                "status": "missing_in_source",
                "source_sql": "",
                "target_sql": generate_create_table_sql(table_name, snap_tables[table_name]),
            })
        else:
            sql1 = generate_create_table_sql(table_name, live_tables[table_name])
            sql2 = generate_create_table_sql(table_name, snap_tables[table_name])
            if sql1 != sql2:
                diffs.append({
                    "type": "tables",
                    "name": table_name,
                    "status": "modified",
                    "source_sql": sql1,
                    "target_sql": sql2,
                })

    # Objects
    for obj_type in OBJECT_TYPES:
        live_objs = live_objects.get(obj_type, {})
        snap_objs = schema.get(obj_type, {})

        for name in set(live_objs.keys()) | set(snap_objs.keys()):
            if name in live_objs and name not in snap_objs:
                diffs.append({
                    "type": obj_type,
                    "name": name,
                    "status": "missing_in_target",
                    "source_sql": normalize(live_objs[name]),
                    "target_sql": "",
                })
            elif name in snap_objs and name not in live_objs:
                diffs.append({
                    "type": obj_type,
                    "name": name,
                    "status": "missing_in_source",
                    "source_sql": "",
                    "target_sql": normalize(snap_objs[name]),
                })
            else:
                sql1 = normalize(live_objs[name])
                sql2 = normalize(snap_objs[name])
                if sql1 != sql2:
                    diffs.append({
                        "type": obj_type,
                        "name": name,
                        "status": "modified",
                        "source_sql": sql1,
                        "target_sql": sql2,
                    })

    log.info("Live vs snapshot comparison: %d differences", len(diffs))
    return diffs
