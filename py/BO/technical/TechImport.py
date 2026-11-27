# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Technical PG dump-like import of a single project.
#
import json
import os
import shutil
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any, Dict, IO, List, Optional, Tuple

from DB.Project import Project
from DB.helpers import Session
from DB.helpers.DDL import Sequence
from helpers.CustomException import UnprocessableEntityException
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)

COPY_CHUNK_SIZE = 1024 * 1024


class TechnicalImport:
    """
    Restore a PostgreSQL COPY-based dump of a single project and its vault images
    from a .tar.zst file, a .tar file, or an extracted directory.
    """

    IMAGES_REPORT_INTERVAL_SECONDS: float = 5.0

    # Must match TechnicalDump._table_queries dependency order
    IMPORT_TABLE_ORDER: Tuple[str, ...] = (
        "projects",
        "projectspriv",
        "projects_taxo_stat",
        "projects_variables",
        "taxo_recast",
        "collection_project",
        "user_preferences",
        "training",
        "samples",
        "acquisitions",
        "process",
        "obj_head",
        "obj_field",
        "images",
        "image_file",
        "objectsclassifhisto",
        "obj_cnn_features_vector",
        "prediction",
        "prediction_histo",
    )

    def __init__(self, session: Session, vault_dir: str):
        self.session = session
        self.vault_dir = vault_dir
        self._log_prefix: str = "Importing: "
        self._project_id: Optional[int] = None

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

    def _copy_table_stream(
        self,
        cur: Any,
        table_name: str,
        src: IO[bytes],
        columns: Optional[List[str]] = None,
    ) -> int:
        cols_sql = ""
        if columns:
            quoted_cols = ", ".join(f'"{c}"' for c in columns)
            cols_sql = f" ({quoted_cols})"

        if table_name == "training":
            # A referenced training row (e.g. shared model) may already exist in target DB
            cur.execute(
                "CREATE TEMP TABLE IF NOT EXISTS _tmp_training (LIKE training) ON COMMIT DROP"
            )
            cur.execute("TRUNCATE _tmp_training")
            with cur.copy(f"COPY _tmp_training{cols_sql} FROM STDIN") as copy:
                while True:
                    chunk = src.read(COPY_CHUNK_SIZE)
                    if not chunk:
                        break
                    copy.write(chunk)
            cur.execute(
                "INSERT INTO training SELECT * FROM _tmp_training "
                "ON CONFLICT (training_id) DO NOTHING"
            )
            return max(cur.rowcount or 0, 0)

        with cur.copy(f"COPY {table_name}{cols_sql} FROM STDIN") as copy:
            while True:
                chunk = src.read(COPY_CHUNK_SIZE)
                if not chunk:
                    break
                copy.write(chunk)
        return max(cur.rowcount or 0, 0)

    def _reset_sequences(self, cur: Any, imported_tables: set[str]) -> None:
        for a_table in Project.metadata.sorted_tables:
            if a_table.name not in imported_tables:
                continue
            for a_col in a_table.columns:
                if isinstance(a_col.default, Sequence):
                    cur.execute(
                        f"SELECT setval(%s, GREATEST(COALESCE((SELECT max({a_col.name}) FROM {a_table.name}), 0), 1), "
                        f"(SELECT count(*) > 0 FROM {a_table.name}))",
                        (a_col.default.name,),
                    )

    def _parse_metadata(self, meta_bytes: bytes) -> Dict[str, List[str]]:
        metadata = json.loads(meta_bytes.decode("utf-8"))
        prj_id = metadata.get("project_id")
        if prj_id is not None:
            self._project_id = int(prj_id)
            self._log_prefix = f"Importing {prj_id}: "
        table_columns: Dict[str, List[str]] = {}
        for tbl in metadata.get("tables", []):
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

    @staticmethod
    def _resolve_dir_root(dir_path: Path) -> Path:
        if (dir_path / "0_metadata.json").is_file() or (
            dir_path / "01_projects.copy"
        ).is_file():
            return dir_path
        children = [p for p in dir_path.iterdir() if p.is_dir()]
        if len(children) == 1:
            sub = children[0]
            if (sub / "0_metadata.json").is_file() or (
                sub / "01_projects.copy"
            ).is_file():
                return sub
        return dir_path

    def _import_from_directory(
        self, dir_path: Path, cur: Any
    ) -> Tuple[Dict[str, int], int]:
        root = self._resolve_dir_root(dir_path)
        meta_path = root / "0_metadata.json"
        table_columns: Dict[str, List[str]] = {}
        if meta_path.is_file():
            table_columns = self._parse_metadata(meta_path.read_bytes())

        logger.info(
            "%sStarting technical import from directory %s", self._log_prefix, root
        )
        row_counts: Dict[str, int] = {}
        copy_files_by_table: Dict[str, Path] = {}
        for entry in root.iterdir():
            if entry.is_file():
                tbl = self._table_from_copy_filename(entry.name)
                if tbl is not None:
                    copy_files_by_table[tbl] = entry

        if not copy_files_by_table:
            raise UnprocessableEntityException(
                f"No project .copy files found in directory: {dir_path.name}"
            )

        for table_name in self.IMPORT_TABLE_ORDER:
            copy_path = copy_files_by_table.get(table_name)
            if copy_path is None:
                continue
            with open(copy_path, "rb") as f:
                rows = self._copy_table_stream(
                    cur, table_name, f, columns=table_columns.get(table_name)
                )
            row_counts[table_name] = rows
            logger.info(
                "%sImported %d rows into %s from %s",
                self._log_prefix,
                rows,
                table_name,
                copy_path.name,
            )

        vault_files = 0
        vault_src = root / "vault"
        if vault_src.is_dir():
            logger.info("%sRestoring vault images", self._log_prefix)
            last_report_at = time.monotonic()
            for dirpath, _dirnames, filenames in os.walk(vault_src):
                for fname in sorted(filenames):
                    src_file = Path(dirpath) / fname
                    rel_sub = src_file.relative_to(vault_src).as_posix()
                    with open(src_file, "rb") as f:
                        self._copy_vault_file(rel_sub, f)
                    vault_files += 1
                    now = time.monotonic()
                    if now - last_report_at >= self.IMAGES_REPORT_INTERVAL_SECONDS:
                        last_report_at = now
                        logger.info(
                            "%sRestored %d vault files", self._log_prefix, vault_files
                        )
            logger.info("%sRestored %d vault files", self._log_prefix, vault_files)

        return row_counts, vault_files

    def _import_from_tar(
        self, archive_path: Path, tar_mode: str, cur: Any
    ) -> Tuple[Dict[str, int], int]:
        logger.info(
            "%sStarting technical import from archive %s",
            self._log_prefix,
            archive_path.name,
        )
        table_columns: Dict[str, List[str]] = {}
        row_counts: Dict[str, int] = {}
        deferred_copies: Dict[str, IO[bytes]] = {}
        next_table_idx = 0
        vault_files = 0
        last_report_at = time.monotonic()
        vault_started = False

        def _flush_ready_deferred() -> None:
            nonlocal next_table_idx
            while next_table_idx < len(self.IMPORT_TABLE_ORDER):
                expected_tbl = self.IMPORT_TABLE_ORDER[next_table_idx]
                buf = deferred_copies.pop(expected_tbl, None)
                if buf is None:
                    break
                try:
                    buf.seek(0)
                    rows = self._copy_table_stream(
                        cur,
                        expected_tbl,
                        buf,
                        columns=table_columns.get(expected_tbl),
                    )
                    row_counts[expected_tbl] = rows
                    logger.info(
                        "%sImported %d rows into %s",
                        self._log_prefix,
                        rows,
                        expected_tbl,
                    )
                finally:
                    buf.close()
                next_table_idx += 1

        try:
            with tarfile.open(name=archive_path, mode=tar_mode) as tfile:  # type: ignore[call-overload]
                for member in tfile:
                    if not member.isfile():
                        continue
                    norm_name = self._normalize_member_name(member.name)
                    if norm_name == "0_metadata.json":
                        extracted = tfile.extractfile(member)
                        if extracted is not None:
                            table_columns = self._parse_metadata(extracted.read())
                        continue

                    if "/" not in norm_name:
                        tbl = self._table_from_copy_filename(norm_name)
                        if tbl is not None:
                            extracted = tfile.extractfile(member)
                            if extracted is None:
                                continue
                            # Stream directly if this table is the next expected one (or all predecessors are done)
                            tbl_idx = self.IMPORT_TABLE_ORDER.index(tbl)
                            if tbl_idx == next_table_idx:
                                rows = self._copy_table_stream(
                                    cur,
                                    tbl,
                                    extracted,
                                    columns=table_columns.get(tbl),
                                )
                                row_counts[tbl] = rows
                                logger.info(
                                    "%sImported %d rows into %s from %s",
                                    self._log_prefix,
                                    rows,
                                    tbl,
                                    norm_name,
                                )
                                next_table_idx += 1
                                _flush_ready_deferred()
                            else:
                                # Out-of-order archive: spool until predecessors are imported
                                tmp = tempfile.SpooledTemporaryFile(
                                    max_size=16 * 1024 * 1024
                                )
                                shutil.copyfileobj(
                                    extracted, tmp, length=COPY_CHUNK_SIZE
                                )
                                deferred_copies[tbl] = tmp
                            continue

                    if norm_name.startswith("vault/"):
                        # Flush any remaining deferred DB tables before vault files
                        while next_table_idx < len(self.IMPORT_TABLE_ORDER):
                            if (
                                self.IMPORT_TABLE_ORDER[next_table_idx]
                                in deferred_copies
                            ):
                                _flush_ready_deferred()
                            else:
                                next_table_idx += 1
                        if not vault_started:
                            vault_started = True
                            last_report_at = time.monotonic()
                            logger.info("%sRestoring vault images", self._log_prefix)
                        extracted = tfile.extractfile(member)
                        if extracted is None:
                            continue
                        rel_sub = norm_name[len("vault/") :]
                        self._copy_vault_file(rel_sub, extracted)
                        vault_files += 1
                        now = time.monotonic()
                        if now - last_report_at >= self.IMAGES_REPORT_INTERVAL_SECONDS:
                            last_report_at = now
                            logger.info(
                                "%sRestored %d vault files",
                                self._log_prefix,
                                vault_files,
                            )
        finally:
            # Ensure any remaining deferred buffers are flushed or closed
            while next_table_idx < len(self.IMPORT_TABLE_ORDER) and deferred_copies:
                if self.IMPORT_TABLE_ORDER[next_table_idx] in deferred_copies:
                    _flush_ready_deferred()
                else:
                    next_table_idx += 1
            for buf in deferred_copies.values():
                buf.close()

        if not row_counts:
            raise UnprocessableEntityException(
                f"No project .copy files found in archive: {archive_path.name}"
            )
        if vault_started:
            logger.info("%sRestored %d vault files", self._log_prefix, vault_files)

        return row_counts, vault_files

    def import_project(self, source_path: Path) -> Dict[str, Any]:
        """
        Restore a project from a .tar.zst file, .tar file, or directory.
        Returns a summary dict with project_id, rowcount, tables, and vault_files.
        """
        started_at = time.monotonic()
        sa_conn = self.session.connection()
        raw_conn: Any = sa_conn.connection.driver_connection
        assert raw_conn is not None, "Missing DBAPI driver connection"

        with raw_conn.cursor() as cur:
            if source_path.is_dir():
                row_counts, vault_files = self._import_from_directory(source_path, cur)
            elif source_path.is_file():
                lower_name = source_path.name.lower()
                if lower_name.endswith(".tar.zst"):
                    tar_mode = "r:zst"
                elif lower_name.endswith(".tar"):
                    tar_mode = "r:"
                else:
                    raise UnprocessableEntityException(
                        f"Unsupported archive format for '{source_path.name}': expected .tar, .tar.zst, or directory"
                    )
                row_counts, vault_files = self._import_from_tar(
                    source_path, tar_mode, cur
                )
            else:
                raise UnprocessableEntityException(
                    f"Archive path is neither a file nor a directory: {source_path.name}"
                )

            self._reset_sequences(cur, set(row_counts.keys()))

            imported_proj_id: Optional[int] = self._project_id
            if imported_proj_id is None:
                cur.execute("SELECT projid FROM projects ORDER BY projid DESC LIMIT 1")
                proj_row = cur.fetchone()
                imported_proj_id = int(proj_row[0]) if proj_row is not None else None

        self.session.commit()

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
