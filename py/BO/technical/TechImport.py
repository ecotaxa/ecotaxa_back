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

from DB.Acquisition import Acquisition
from DB.CNNFeatureVector import ObjectCNNFeatureVector
from DB.Collection import Collection, CollectionProject
from DB.Image import Image, ImageFile
from DB.Instrument import Instrument
from DB.Object import ObjectFields, ObjectHeader, ObjectsClassifHisto
from DB.Prediction import Prediction, PredictionHisto
from DB.Process import Process
from DB.Project import Project, ProjectTaxoStat
from DB.ProjectPrivilege import ProjectPrivilege
from DB.ProjectVariables import ProjectVariables
from DB.Sample import Sample
from DB.TaxoRecast import TaxoRecast
from DB.Taxonomy import Taxonomy
from DB.Training import Training
from DB.User import Organization, User
from DB.UserPreferences import UserPreferences
from DB.helpers import Session
from DB.helpers.DDL import Sequence
from helpers.CustomException import UnprocessableEntityException
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)

COPY_CHUNK_SIZE = 1024 * 1024

ProgressCallback = Callable[[int, str], None]


@dataclass
class _TarImportState:
    cur: Any
    table_columns: Dict[str, List[str]] = field(default_factory=dict)
    metadata_seen: bool = False
    row_counts: Dict[str, int] = field(default_factory=dict)
    next_table_idx: int = 0
    vault_files: int = 0
    vault_started: bool = False
    last_report_at: float = field(default_factory=time.monotonic)


class TechnicalImport:
    """
    Restore a PostgreSQL COPY-based dump of a single project and its vault images
    from a .tar.zst file.
    """

    IMAGES_REPORT_INTERVAL_SECONDS: float = 5.0

    _IMPORT_MODELS: Tuple[Any, ...] = (
        Instrument,
        Organization,
        User,
        Taxonomy,
        Collection,
        Project,
        ProjectPrivilege,
        ProjectTaxoStat,
        ProjectVariables,
        TaxoRecast,
        CollectionProject,
        UserPreferences,
        Training,
        Sample,
        Acquisition,
        Process,
        ObjectHeader,
        ObjectFields,
        Image,
        ImageFile,
        ObjectsClassifHisto,
        ObjectCNNFeatureVector,
        Prediction,
        PredictionHisto,
    )
    _CONFLICT_TOLERANT_TABLES: Tuple[str, ...] = (
        Instrument.__tablename__,
        Organization.__tablename__,
        User.__tablename__,
        Taxonomy.__tablename__,
        Collection.__tablename__,
        Training.__tablename__,
    )

    # Must match TechnicalDump._table_queries dependency order
    IMPORT_TABLE_ORDER: Tuple[str, ...] = tuple(m.__tablename__ for m in _IMPORT_MODELS)

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
    def _copy_table_stream(
        cur: Any,
        table_name: str,
        src: IO[bytes],
        columns: List[str],
    ) -> int:
        quoted_cols = ", ".join(f'"{c}"' for c in columns)
        cols_sql = f" ({quoted_cols})"

        if table_name in TechnicalImport._CONFLICT_TOLERANT_TABLES:
            # Shared/reference rows may already exist in target DB
            tmp_table = f"_tmp_{table_name}"
            cur.execute(
                f"CREATE TEMP TABLE IF NOT EXISTS {tmp_table} (LIKE {table_name}) ON COMMIT DROP"
            )
            cur.execute(f"TRUNCATE {tmp_table}")
            with cur.copy(f"COPY {tmp_table}{cols_sql} FROM STDIN") as copy:
                while True:
                    chunk = src.read(COPY_CHUNK_SIZE)
                    if not chunk:
                        break
                    copy.write(chunk)
            cur.execute(
                f"INSERT INTO {table_name}{cols_sql} "
                f"SELECT {quoted_cols} FROM {tmp_table} "
                "ON CONFLICT DO NOTHING"
            )
            return max(cur.rowcount or 0, 0)

        with cur.copy(f"COPY {table_name}{cols_sql} FROM STDIN") as copy:
            while True:
                chunk = src.read(COPY_CHUNK_SIZE)
                if not chunk:
                    break
                copy.write(chunk)
        return max(cur.rowcount or 0, 0)

    @staticmethod
    def _reset_sequences(cur: Any, imported_tables: set[str]) -> None:
        for a_table in Project.metadata.sorted_tables:
            if a_table.name not in imported_tables:
                continue
            for a_col in a_table.columns:
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
                    cur.execute(
                        f"SELECT setval(%s, GREATEST(COALESCE((SELECT max({a_col.name}) FROM {a_table.name}), 0), 1), "
                        f"(SELECT count(*) > 0 FROM {a_table.name}))",
                        (seq_name,),
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

    def _import_table_stream(
        self,
        cur: Any,
        table_name: str,
        src: IO[bytes],
        table_columns: Dict[str, List[str]],
        row_counts: Dict[str, int],
        source_name: Optional[str] = None,
    ) -> None:
        rows = self._copy_table_stream(
            cur,
            table_name,
            src,
            columns=self._require_table_columns(table_columns, table_name),
        )
        row_counts[table_name] = rows
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
        self._import_table_stream(
            state.cur,
            tbl,
            extracted,
            state.table_columns,
            state.row_counts,
            source_name=norm_name,
        )
        state.next_table_idx = tbl_idx + 1

    def _handle_tar_vault_member(
        self,
        tfile: tarfile.TarFile,
        member: tarfile.TarInfo,
        norm_name: str,
        state: _TarImportState,
        vault_progress_start: int = 75,
        progress_end: int = 99,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> None:
        if not state.vault_started:
            state.vault_started = True
            state.last_report_at = time.monotonic()
            logger.info("%sRestoring vault images", self._log_prefix)
            if progress_cb is not None:
                progress_cb(vault_progress_start, "Restoring vault images")
        extracted = tfile.extractfile(member)
        if extracted is None:
            return
        rel_sub = norm_name[len("vault/") :]
        self._copy_vault_file(rel_sub, extracted)
        state.vault_files += 1
        now = time.monotonic()
        if now - state.last_report_at >= self.IMAGES_REPORT_INTERVAL_SECONDS:
            state.last_report_at = now
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
        cur: Any,
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
        state = _TarImportState(cur=cur)
        with tarfile.open(name=archive_path, mode="r:zst") as tfile:
            for member in tfile:
                if not member.isfile():
                    continue
                norm_name = self._normalize_member_name(member.name)
                if norm_name == "0_metadata.json":
                    extracted = tfile.extractfile(member)
                    if extracted is not None:
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
                        state,
                        vault_progress_start=vault_progress_start,
                        progress_end=progress_end,
                        progress_cb=progress_cb,
                    )
        if not state.metadata_seen:
            raise UnprocessableEntityException(
                f"Missing 0_metadata.json in archive: {archive_path.name}"
            )

        if not state.row_counts:
            raise UnprocessableEntityException(
                f"No project .copy files found in archive: {archive_path.name}"
            )
        if state.vault_started:
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
    ) -> Dict[str, Any]:
        """
        Restore a project from a .tar.zst file.
        Returns a summary dict with project_id, rowcount, tables, and vault_files.
        """
        if not source_path.is_file() or not source_path.name.lower().endswith(".tar.zst"):
            raise UnprocessableEntityException(
                f"Unsupported archive format for '{source_path.name}': expected a .tar.zst file"
            )

        started_at = time.monotonic()
        sa_conn = self.session.connection()
        raw_conn: Any = sa_conn.connection.driver_connection
        assert raw_conn is not None, "Missing DBAPI driver connection"

        with raw_conn.cursor() as cur:
            row_counts, vault_files = self._import_from_tar(
                source_path,
                cur,
                progress_start=progress_start,
                progress_end=progress_end,
                progress_cb=progress_cb,
            )

            if progress_cb is not None:
                progress_cb(progress_end, "Resetting sequences")
            self._reset_sequences(cur, set(row_counts.keys()))

            imported_proj_id: Optional[int] = self._project_id
            if imported_proj_id is None:
                cur.execute(
                    f"SELECT projid FROM {Project.__tablename__} ORDER BY projid DESC LIMIT 1"
                )
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
