# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# PostgreSQL schema metadata builder for technical project dumps (0_metadata.json).
#
from typing import Any, Dict, List, Optional, Tuple

from helpers import DateTime


def _fetch_postgres_version(cur: Any) -> Optional[str]:
    cur.execute("SELECT version()")
    row = cur.fetchone()
    return row[0] if row else None


def _fetch_alembic_version(cur: Any) -> Optional[str]:
    cur.execute("SELECT to_regclass('alembic_version')")
    if cur.fetchone()[0] is None:
        return None  # Does not exist on DB from scratch
    cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
    row = cur.fetchone()
    return row[0] if row is not None else None


def _fetch_table_columns(
    cur: Any, table_name: str, model_columns: List[str]
) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT
            a.attname,
            pg_catalog.format_type(a.atttypid, a.atttypmod),
            NOT a.attnotnull,
            pg_get_expr(d.adbin, d.adrelid)
        FROM pg_catalog.pg_attribute a
        JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
        WHERE n.nspname = 'public'
          AND c.relname = %s
          AND a.attnum > 0
          AND NOT a.attisdropped
        ORDER BY a.attnum
        """,
        (table_name,),
    )
    pg_cols_by_name = {
        col_name: {
            "name": col_name,
            "type": col_type,
            "nullable": bool(nullable),
            "default": col_default,
        }
        for col_name, col_type, nullable, col_default in cur.fetchall()
    }
    return [
        pg_cols_by_name[col_name]
        for col_name in model_columns
        if col_name in pg_cols_by_name
    ]


def _fetch_primary_key(cur: Any, table_name: str) -> List[str]:
    cur.execute(
        """
        SELECT a.attname
        FROM pg_catalog.pg_index i
        JOIN pg_catalog.pg_class c ON c.oid = i.indrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        JOIN unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord) ON true
        JOIN pg_catalog.pg_attribute a ON a.attrelid = c.oid AND a.attnum = k.attnum
        WHERE n.nspname = 'public'
          AND c.relname = %s
          AND i.indisprimary
        ORDER BY k.ord
        """,
        (table_name,),
    )
    return [row[0] for row in cur.fetchall()]


def _fetch_foreign_keys(cur: Any, table_name: str) -> List[Dict[str, str]]:
    cur.execute(
        """
        SELECT
            con.conname,
            pg_get_constraintdef(con.oid)
        FROM pg_catalog.pg_constraint con
        JOIN pg_catalog.pg_class c ON c.oid = con.conrelid
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relname = %s
          AND con.contype = 'f'
        ORDER BY con.conname
        """,
        (table_name,),
    )
    return [
        {"name": fk_name, "definition": fk_def} for fk_name, fk_def in cur.fetchall()
    ]


def _collect_table_metadata(
    cur: Any, idx: int, table_name: str, model_columns: List[str]
) -> Dict[str, Any]:
    return {
        "name": table_name,
        "copy_file": f"{idx:02d}_{table_name}.copy",
        "columns": _fetch_table_columns(cur, table_name, model_columns),
        "primary_key": _fetch_primary_key(cur, table_name),
        "foreign_keys": _fetch_foreign_keys(cur, table_name),
    }


def build_schema_metadata(
    cur: Any,
    project_id: int,
    table_columns: List[Tuple[str, List[str]]],
) -> Dict[str, Any]:
    """
    Build PostgreSQL schema metadata for all exported tables in dependency order.
    """
    return {
        "project_id": project_id,
        "exported_at": DateTime.now_time().isoformat(),
        "format": "pg_copy_tar_zst",
        "postgres_version": _fetch_postgres_version(cur),
        "alembic_version": _fetch_alembic_version(cur),
        "tables": [
            _collect_table_metadata(cur, idx, table_name, cols)
            for idx, (table_name, cols) in enumerate(table_columns, start=1)
        ],
    }
