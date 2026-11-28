# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Technical PG dump-like import of a single project.
#
import json
import shutil
import tarfile
import time
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, IO, List, Optional, Tuple

from psycopg import sql as pgsql

from BO.technical.DumpConfig import (
    TABLE_DUMP_CONFIGS,
    ProgressCallback,
    TableDumpConfig,
    dedup_progress_cb,
)
from DB.Project import Project
from DB.helpers.Connection import Connection
from DB.helpers.DDL import Sequence
from helpers.CustomException import UnprocessableEntityException
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)

COPY_CHUNK_SIZE = 1024 * 1024


@dataclass
class _TarImportState:
    conn: Any
    cur: Any
    table_columns: Dict[str, List[str]] = field(default_factory=dict)
    metadata_seen: bool = False
    row_counts: Dict[str, int] = field(default_factory=dict)
    seq_max_ids: Dict[str, int] = field(default_factory=dict)
    next_table_idx: int = 0
    db_committed: bool = False
    vault_started: bool = False
    vault_files: int = 0
    last_reported_vault_files: int = -1
    last_report_at: float = field(default_factory=time.monotonic)


class TechnicalImport:
    """
    Restore a PostgreSQL COPY-based dump of a single project and its vault images
    from a .tar.zst file.
    """

    IMAGES_REPORT_INTERVAL_SECONDS: float = 5.0

    _CONFIG_BY_TABLE: Dict[str, TableDumpConfig] = {
        cfg.table_name: cfg for cfg in TABLE_DUMP_CONFIGS
    }
    IMPORT_TABLE_ORDER: Tuple[str, ...] = tuple(
        cfg.table_name for cfg in TABLE_DUMP_CONFIGS
    )

    def __init__(self, vault_dir: str):
        self.vault_dir = vault_dir
        self._log_prefix: str = "Importing: "
        self._source_project_id: Optional[int] = None
        self._target_project_id: Optional[int] = None

    @staticmethod
    def _normalize_member_name(name: str) -> str:
        norm = name.lstrip("./") if name.startswith("./") else name
        return norm.lstrip("/")

    @staticmethod
    def _validate_vault_subpath(sub_path: str) -> Path:
        pure = PurePosixPath(sub_path)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts:
            raise UnprocessableEntityException(
                f"Invalid vault path in archive: {sub_path}"
            )
        return Path(*pure.parts)

    @staticmethod
    def _table_from_copy_filename(filename: str) -> Optional[str]:
        if not filename.endswith(".copy"):
            return None
        stem = filename[: -len(".copy")]
        # Expected format: "<NN>_<table_name>"
        if "_" in stem:
            prefix, rest = stem.split("_", 1)
            if prefix.isdigit() and rest in TechnicalImport.IMPORT_TABLE_ORDER:
                return rest
        if stem in TechnicalImport.IMPORT_TABLE_ORDER:
            return stem
        return None

    @staticmethod
    def _require_table_columns(
        table_columns: Dict[str, List[str]], table_name: str
    ) -> List[str]:
        cols = table_columns.get(table_name)
        if not cols:
            raise UnprocessableEntityException(
                f"Missing metadata columns for table '{table_name}'"
            )
        return cols

    @staticmethod
    def _build_column_transforms(
        table_name: str,
        columns: List[str],
        source_project_id: Optional[int],
        target_project_id: Optional[int],
    ) -> List[Tuple[int, Callable[[bytes], bytes]]]:
        if (
            target_project_id is None
            or source_project_id is None
            or target_project_id == source_project_id
        ):
            return []

        cfg = TechnicalImport._CONFIG_BY_TABLE.get(table_name)
        if cfg is None or not cfg.col_offsets:
            return []

        delta_proj = target_project_id - source_project_id
        src_proj_bytes = str(source_project_id).encode("ascii")
        dst_proj_bytes = str(target_project_id).encode("ascii")

        def _replace_proj(val: bytes) -> bytes:
            return dst_proj_bytes if val == src_proj_bytes else val

        def _shift_offset(offset: int) -> Callable[[bytes], bytes]:
            delta = delta_proj * offset

            def _shift(val: bytes) -> bytes:
                if val == b"\\N":  # PostgreSQL COPY text-format NULL marker
                    return val
                return b"%d" % (int(val) + delta)

            return _shift

        transforms: List[Tuple[int, Callable[[bytes], bytes]]] = []
        for idx, col_name in enumerate(columns):
            if col_name not in cfg.col_offsets:
                continue
            col_offset = cfg.col_offsets[col_name]
            fn = _replace_proj if col_offset is None else _shift_offset(col_offset)
            transforms.append((idx, fn))
        return transforms

    @staticmethod
    def _write_copy_stream(
        copy: Any,
        src: IO[bytes],
        transforms: List[Tuple[int, Callable[[bytes], bytes]]],
        track_max_cols: Optional[List[int]] = None,
    ) -> Dict[int, int]:
        """
        Streams COPY-formatted data from a binary source to a COPY writer.

        The stream is written in chunks for efficient transfer. When transformations or
        maximum-value tracking are requested, each row is processed as a tab-delimited
        record before being buffered for output. Selected fields can be transformed, and
        selected columns can be inspected to collect the greatest non-null integer value
        encountered for each tracked column.

        :param copy: Destination COPY writer that receives output chunks through a
            write method.
        :param src: Source stream containing COPY-formatted tab-delimited rows.
        :param transforms: Ordered column transformations represented as column indexes
            paired with callables applied to the corresponding field values.
        :param track_max_cols: Column"""
        max_vals: Dict[int, int] = {}
        if not transforms and not track_max_cols:
            while True:
                chunk = src.read(COPY_CHUNK_SIZE)
                if not chunk:
                    break
                copy.write(chunk)
            return max_vals

        return TechnicalImport._write_copy_stream_transformed(
            copy, max_vals, src, track_max_cols, transforms
        )

    @staticmethod
    def _write_copy_stream_transformed(
        copy: Any,
        max_vals: dict[int, int],
        src: IO[bytes],
        track_max_cols: list[int] | None,
        transforms: list[tuple[int, Callable[[bytes], bytes]]],
    ) -> dict[int, int]:
        # Example PostgreSQL COPY text-format input (tab-delimited, \N = NULL, \n = row end):
        #   100000001\t10001\tcopepoda\t\N\t0.42\n
        #   100000002\t\N\tdiatom\tsome\tnote\t1.25\n
        # With max_split, only the leading columns up to the highest transformed/tracked
        # index are split; any remaining columns stay in fields[-1] as a single bytes tail.
        buf = bytearray()
        tracked = track_max_cols or []
        needed_indices = [idx for idx, _ in transforms]
        needed_indices.extend(tracked)
        max_split = max(needed_indices) + 1  # Keep untouched trailing columns unsplit
        carry = b""
        while True:
            chunk = src.read(COPY_CHUNK_SIZE)
            if chunk:
                data = carry + chunk if carry else chunk
                lines = data.split(b"\n")  # COPY text-format row delimiter
                carry = lines.pop()
                trailing_nl = True
            elif carry:
                lines = [carry]
                carry = b""
                trailing_nl = False
            else:
                break
            for body in lines:
                fields = body.split(
                    b"\t", max_split
                )  # COPY text-format column delimiter
                for idx, fn in transforms:
                    fields[idx] = fn(fields[idx])
                for idx in tracked:
                    raw_val = fields[idx]
                    if raw_val != b"\\N":  # Skip PostgreSQL COPY NULL marker
                        val = int(raw_val)
                        prev = max_vals.get(idx)
                        if prev is None or val > prev:
                            max_vals[idx] = val
                if transforms:
                    buf.extend(b"\t".join(fields))
                else:
                    buf.extend(body)
                if trailing_nl:
                    buf.extend(b"\n")
                if len(buf) >= COPY_CHUNK_SIZE:
                    copy.write(buf)
                    buf.clear()
            if not trailing_nl:
                break
        if buf:
            copy.write(buf)
        return max_vals

    @staticmethod
    def _copy_table_stream(
        cur: Any,
        table_name: str,
        src: IO[bytes],
        columns: List[str],
        transforms: Optional[List[Tuple[int, Callable[[bytes], bytes]]]] = None,
        track_max_cols: Optional[List[int]] = None,
    ) -> Tuple[int, Dict[int, int]]:
        quoted_cols = ", ".join(f'"{c}"' for c in columns)
        cols_sql = f" ({quoted_cols})"
        active_transforms = transforms or []

        cfg = TechnicalImport._CONFIG_BY_TABLE.get(table_name)
        if cfg is not None and cfg.conflict_tolerant:
            # Shared/reference rows may already exist in target DB
            tmp_table = f"_tmp_{table_name}"
            cur.execute(
                f"CREATE TEMP TABLE IF NOT EXISTS {tmp_table} (LIKE {table_name}) ON COMMIT DROP"
            )
            cur.execute(f"TRUNCATE {tmp_table}")
            with cur.copy(f"COPY {tmp_table}{cols_sql} FROM STDIN") as copy:
                max_vals = TechnicalImport._write_copy_stream(
                    copy, src, active_transforms, track_max_cols
                )
            cur.execute(
                f"INSERT INTO {table_name}{cols_sql} "
                f"SELECT {quoted_cols} FROM {tmp_table} "
                "ON CONFLICT DO NOTHING"
            )
            return max(cur.rowcount or 0, 0), max_vals

        pk_spec = cfg.regenerate_pk if cfg is not None else None
        if pk_spec is not None:
            # Surrogate PKs not scoped to project IDs must be freshly assigned on import
            pk_col, pk_expr = pk_spec
            tmp_table = f"_tmp_{table_name}"
            cur.execute(
                f"CREATE TEMP TABLE IF NOT EXISTS {tmp_table} (LIKE {table_name}) ON COMMIT DROP"
            )
            cur.execute(f"TRUNCATE {tmp_table}")
            with cur.copy(f"COPY {tmp_table}{cols_sql} FROM STDIN") as copy:
                max_vals = TechnicalImport._write_copy_stream(
                    copy, src, active_transforms, track_max_cols
                )
            other_cols = [c for c in columns if c != pk_col]
            quoted_other = ", ".join(f'"{c}"' for c in other_cols)
            if pk_expr is not None:
                insert_cols_sql = f'"{pk_col}", {quoted_other}'
                select_cols_sql = f"{pk_expr}, {quoted_other}"
            else:
                insert_cols_sql = quoted_other
                select_cols_sql = quoted_other
            cur.execute(
                f"INSERT INTO {table_name} ({insert_cols_sql}) "
                f"SELECT {select_cols_sql} FROM {tmp_table}"
            )
            return max(cur.rowcount or 0, 0), max_vals

        with cur.copy(f"COPY {table_name}{cols_sql} FROM STDIN") as copy:
            max_vals = TechnicalImport._write_copy_stream(
                copy, src, active_transforms, track_max_cols
            )
        return max(cur.rowcount or 0, 0), max_vals

    @staticmethod
    def _table_sequences(
        cur: Any, table_name: str, columns: List[str]
    ) -> Dict[int, str]:
        """
        Determine sequence metadata for columns that can be populated by database-managed
        values during import processing.

        The lookup inspects the mapped table metadata and detects explicit SQLAlchemy
        sequences, identity columns, serial columns, and auto-incrementing primary-key
        columns. Tables configured to regenerate primary keys, unknown tables, unknown
        columns, and columns without an associated sequence are ignored.

        :param cur: Database cursor used to query PostgreSQL serial sequence metadata.
        :param table_name: Name of the table whose column sequences are inspected.
        :param columns: Ordered column names matching the import column order.
        :return: Mapping from each zero-based column position to the associated database
            sequence name.
        """
        cfg = TechnicalImport._CONFIG_BY_TABLE.get(table_name)
        if cfg is not None and cfg.regenerate_pk is not None:
            return {}
        a_table = Project.metadata.tables.get(table_name)
        if a_table is None:
            return {}
        col_seqs: Dict[int, str] = {}
        for idx, col_name in enumerate(columns):
            a_col = a_table.columns.get(col_name)
            if a_col is None:
                continue
            seq_name: Optional[str] = None
            if isinstance(a_col.default, Sequence):
                seq_name = a_col.default.name
            elif a_col.identity is not None or (
                a_col.primary_key and a_col.autoincrement is not False
            ):
                cur.execute(
                    "SELECT pg_get_serial_sequence(%s, %s)",
                    (a_table.name, a_col.name),
                )
                row = cur.fetchone()
                if row and row[0]:
                    seq_name = row[0]
            if seq_name is not None:
                col_seqs[idx] = seq_name
        return col_seqs

    @staticmethod
    def _sequence_relation(cur: Any, seq_name: str) -> Optional[Tuple[str, str]]:
        """
        Resolve a (possibly schema-qualified) sequence name to its schema and
        relation name via the catalog, so that it can be safely quoted as an
        SQL identifier instead of being interpolated into the query.
        """
        cur.execute(
            """
            SELECT n.nspname, c.relname
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.oid = to_regclass(%s)
            """,
            (seq_name,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return str(row[0]), str(row[1])

    @staticmethod
    def _reset_sequences(cur: Any, seq_max_ids: Dict[str, int]) -> None:
        for seq_name, max_id in seq_max_ids.items():
            relation = TechnicalImport._sequence_relation(cur, seq_name)
            if relation is None:
                continue
            schema_name, rel_name = relation
            cur.execute(
                pgsql.SQL("SELECT last_value, is_called FROM {}").format(
                    pgsql.Identifier(schema_name, rel_name)
                )
            )
            row = cur.fetchone()
            if row is None:
                continue
            last_value, is_called = row
            if max_id > last_value or (not is_called and max_id >= last_value):
                cur.execute("SELECT setval(%s, %s, true)", (seq_name, max_id))

    def _parse_metadata(self, meta_bytes: bytes) -> Dict[str, List[str]]:
        metadata = json.loads(meta_bytes.decode("utf-8"))
        prj_id = metadata.get("project_id")
        if prj_id is None:
            raise UnprocessableEntityException("Missing project_id in 0_metadata.json")
        self._source_project_id = int(prj_id)
        if self._target_project_id is None:
            self._target_project_id = self._source_project_id
        if self._target_project_id != self._source_project_id:
            self._log_prefix = (
                f"Importing {self._source_project_id}->{self._target_project_id}: "
            )
        else:
            self._log_prefix = f"Importing {self._target_project_id}: "
        tables = metadata.get("tables")
        if not isinstance(tables, list):
            raise UnprocessableEntityException("Missing tables in 0_metadata.json")
        table_columns: Dict[str, List[str]] = {}
        for tbl in tables:
            name = tbl.get("name")
            cols = [c["name"] for c in tbl.get("columns", []) if "name" in c]
            if name in self.IMPORT_TABLE_ORDER and cols:
                table_columns[name] = cols
        return table_columns

    def _copy_vault_file(self, rel_sub_path: str, src: IO[bytes]) -> None:
        rel_path = self._validate_vault_subpath(rel_sub_path)
        dest_path = Path(self.vault_dir) / rel_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as dst:
            shutil.copyfileobj(src, dst, length=COPY_CHUNK_SIZE)

    def _import_table_stream(
        self,
        cur: Any,
        table_name: str,
        src: IO[bytes],
        table_columns: Dict[str, List[str]],
        row_counts: Dict[str, int],
        seq_max_ids: Optional[Dict[str, int]] = None,
        source_name: Optional[str] = None,
    ) -> None:
        columns = self._require_table_columns(table_columns, table_name)
        transforms = self._build_column_transforms(
            table_name,
            columns,
            self._source_project_id,
            self._target_project_id,
        )
        col_seqs = self._table_sequences(cur, table_name, columns)
        rows, max_vals = self._copy_table_stream(
            cur,
            table_name,
            src,
            columns=columns,
            transforms=transforms,
            track_max_cols=list(col_seqs.keys()),
        )
        row_counts[table_name] = rows
        if seq_max_ids is not None and rows > 0:
            for idx, max_val in max_vals.items():
                seq_name = col_seqs[idx]
                prev = seq_max_ids.get(seq_name)
                if prev is None or max_val > prev:
                    seq_max_ids[seq_name] = max_val
        if source_name is not None:
            logger.info(
                "%sImported %d rows into %s from %s",
                self._log_prefix,
                rows,
                table_name,
                source_name,
            )
        else:
            logger.info(
                "%sImported %d rows into %s",
                self._log_prefix,
                rows,
                table_name,
            )

    def _handle_tar_copy_member(
        self,
        tfile: tarfile.TarFile,
        member: tarfile.TarInfo,
        norm_name: str,
        state: _TarImportState,
        progress_start: int = 1,
        vault_progress_start: int = 75,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        if not norm_name.endswith(".copy"):
            return
        if not state.metadata_seen:
            raise UnprocessableEntityException(
                f"Unexpected table file '{norm_name}' before 0_metadata.json"
            )
        if state.vault_started:
            raise UnprocessableEntityException(
                f"Unexpected table file '{norm_name}' after vault files"
            )
        tbl = self._table_from_copy_filename(norm_name)
        if tbl is None:
            raise UnprocessableEntityException(
                f"Unexpected table file '{norm_name}' in archive"
            )
        tbl_idx = self.IMPORT_TABLE_ORDER.index(tbl)
        if tbl_idx < state.next_table_idx:
            raise UnprocessableEntityException(
                f"Unexpected out-of-order table '{tbl}' in archive (file '{norm_name}')"
            )
        if progress_cb is not None:
            pct = progress_start + int(
                (vault_progress_start - progress_start)
                * tbl_idx
                / len(self.IMPORT_TABLE_ORDER)
            )
            progress_cb(pct, f"Importing table {tbl}")
        extracted = tfile.extractfile(member)
        if extracted is None:
            return
        with extracted:
            self._import_table_stream(
                state.cur,
                tbl,
                extracted,
                state.table_columns,
                state.row_counts,
                seq_max_ids=state.seq_max_ids,
                source_name=norm_name,
            )
        state.next_table_idx = tbl_idx + 1

    def _commit_db_import(
        self,
        state: _TarImportState,
        archive_name: str,
        seq_progress_pct: int,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        if state.db_committed:
            return
        if not state.metadata_seen:
            raise UnprocessableEntityException(
                f"Missing 0_metadata.json in archive: {archive_name}"
            )
        if not state.row_counts:
            raise UnprocessableEntityException(
                f"No project .copy files found in archive: {archive_name}"
            )
        if progress_cb is not None:
            progress_cb(seq_progress_pct, "Resetting sequences")
        self._reset_sequences(state.cur, state.seq_max_ids)
        state.conn.commit()
        state.db_committed = True
        # Nothing after this point needs the database: release the server-side
        # connection before the potentially long vault extraction phase.
        state.cur.close()
        state.conn.close()

    def _handle_tar_vault_member(
        self,
        tfile: tarfile.TarFile,
        member: tarfile.TarInfo,
        norm_name: str,
        archive_name: str,
        state: _TarImportState,
        vault_progress_start: int = 75,
        progress_end: int = 99,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        if not state.vault_started:
            if not state.metadata_seen:
                raise UnprocessableEntityException(
                    f"Unexpected vault file '{norm_name}' before 0_metadata.json"
                )
            # Commit DB changes and release locks before potentially long vault file extraction.
            self._commit_db_import(
                state,
                archive_name,
                seq_progress_pct=vault_progress_start,
                progress_cb=progress_cb,
            )
            state.vault_started = True
            state.last_report_at = time.monotonic()
            logger.info("%sRestoring vault images", self._log_prefix)
            if progress_cb is not None:
                progress_cb(vault_progress_start, "Restoring vault images")
        extracted = tfile.extractfile(member)
        if extracted is None:
            return
        rel_sub = norm_name[len("vault/") :]
        with extracted:
            self._copy_vault_file(rel_sub, extracted)
        state.vault_files += 1
        now = time.monotonic()
        if now - state.last_report_at >= self.IMAGES_REPORT_INTERVAL_SECONDS:
            state.last_report_at = now
            state.last_reported_vault_files = state.vault_files
            msg = f"Restored {state.vault_files} vault files"
            logger.info(
                "%s%s",
                self._log_prefix,
                msg,
            )
            if progress_cb is not None:
                pct = min(
                    progress_end - 1,
                    vault_progress_start + (state.vault_files // 100),
                )
                progress_cb(pct, msg)

    def _import_from_tar(
        self,
        archive_path: Path,
        state: _TarImportState,
        progress_start: int = 1,
        progress_end: int = 99,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> Tuple[Dict[str, int], int]:
        logger.info(
            "%sStarting technical import from archive %s",
            self._log_prefix,
            archive_path.name,
        )
        vault_progress_start = max(progress_start, progress_end - 25)
        with tarfile.open(name=archive_path, mode="r:zst") as tfile:
            for member in tfile:
                if not member.isfile():
                    continue
                norm_name = self._normalize_member_name(member.name)
                if norm_name == "0_metadata.json":
                    extracted = tfile.extractfile(member)
                    if extracted is not None:
                        with extracted:
                            state.table_columns = self._parse_metadata(extracted.read())
                    state.metadata_seen = True
                elif "/" not in norm_name:
                    self._handle_tar_copy_member(
                        tfile,
                        member,
                        norm_name,
                        state,
                        progress_start=progress_start,
                        vault_progress_start=vault_progress_start,
                        progress_cb=progress_cb,
                    )
                elif norm_name.startswith("vault/"):
                    self._handle_tar_vault_member(
                        tfile,
                        member,
                        norm_name,
                        archive_path.name,
                        state,
                        vault_progress_start=vault_progress_start,
                        progress_end=progress_end,
                        progress_cb=progress_cb,
                    )
        self._commit_db_import(
            state,
            archive_path.name,
            seq_progress_pct=progress_end,
            progress_cb=progress_cb,
        )
        if state.vault_started and state.vault_files != state.last_reported_vault_files:
            msg = f"Restored {state.vault_files} vault files"
            logger.info("%s%s", self._log_prefix, msg)
            if progress_cb is not None:
                progress_cb(progress_end - 1, msg)

        return state.row_counts, state.vault_files

    def import_project(
        self,
        source_path: Path,
        progress_start: int = 1,
        progress_end: int = 99,
        progress_cb: Optional[ProgressCallback] = None,
        target_project_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Restore a project from a .tar.zst file.
        If target_project_id is provided, all project-scoped data is remapped to that project ID.
        Returns a summary dict with project_id, rowcount, tables, and vault_files.
        """
        if target_project_id is not None and target_project_id <= 0:
            raise UnprocessableEntityException(
                f"Invalid target_project_id: {target_project_id}"
            )
        self._target_project_id = target_project_id
        if not source_path.is_file() or not source_path.name.lower().endswith(
            ".tar.zst"
        ):
            raise UnprocessableEntityException(
                f"Unsupported archive format for '{source_path.name}': expected a .tar.zst file"
            )

        progress_cb = dedup_progress_cb(progress_cb)
        started_at = time.monotonic()

        state: Optional[_TarImportState] = None
        with Connection.get_raw_psycopg_connection(read_only=False) as raw_conn:
            try:
                with raw_conn.cursor() as cur:
                    state = _TarImportState(conn=raw_conn, cur=cur)
                    row_counts, vault_files = self._import_from_tar(
                        source_path,
                        state,
                        progress_start=progress_start,
                        progress_end=progress_end,
                        progress_cb=progress_cb,
                    )

                    assert (
                        self._target_project_id is not None
                    ), "Missing project_id from metadata"
                    imported_proj_id: int = self._target_project_id
            except Exception:
                if state is None or not state.db_committed:
                    try:
                        raw_conn.rollback()
                    except Exception:
                        pass
                raise

        total_rows = sum(row_counts.values())
        logger.info(
            "%sFinished import (%d total rows, %d vault files in %.1fs)",
            self._log_prefix,
            total_rows,
            vault_files,
            time.monotonic() - started_at,
        )
        return {
            "project_id": imported_proj_id,
            "rowcount": total_rows,
            "tables": row_counts,
            "vault_files": vault_files,
        }
