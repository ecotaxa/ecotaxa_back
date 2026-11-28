# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Technical PG dump-like export of a single project.
#
import compression.zstd as zstd
import io
import json
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, IO, List, Optional, Tuple

from psycopg import IsolationLevel

from BO.technical.DumpConfig import (
    TABLE_DUMP_CONFIGS,
    ProgressCallback,
    dedup_progress_cb,
)
from BO.technical.TechMetadata import build_schema_metadata
from DB.Acquisition import Acquisition
from DB.CNNFeatureVector import ObjectCNNFeatureVector
from DB.Collection import Collection, CollectionProject
from DB.Image import Image, ImageFile
from DB.Instrument import Instrument
from DB.Object import ObjectFields, ObjectHeader, ObjectsClassifHisto
from DB.Prediction import Prediction, PredictionHisto
from DB.Process import Process
from DB.Project import Project, ProjectIDT, ProjectTaxoStat
from DB.ProjectPrivilege import ProjectPrivilege
from DB.ProjectVariables import ProjectVariables
from DB.Sample import Sample
from DB.TaxoRecast import TaxoRecast
from DB.Taxonomy import Taxonomy
from DB.Training import Training
from DB.User import Organization, User
from DB.UserPreferences import UserPreferences
from DB.helpers import SQL
from DB.helpers.Connection import Connection
from FS.Vault import Vault
from helpers import DateTime
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class _PhasedZstdStream(io.RawIOBase):
    """
    Writable stream that compresses into concatenated zstd frames, allowing
    the compression level to be switched between phases of a single tar stream.
    """

    def __init__(self, raw: Any, level: int) -> None:
        self._raw = raw
        self._comp: Optional[zstd.ZstdCompressor] = zstd.ZstdCompressor(level=level)
        self._pos: int = 0

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def tell(self) -> int:
        return self._pos

    def write(self, b: Any) -> int:
        assert self._comp is not None, "Stream is closed"
        data = bytes(b)
        if data:
            out = self._comp.compress(data)
            if out:
                self._raw.write(out)
            self._pos += len(data)
        return len(data)

    def switch_level(self, level: int) -> None:
        assert self._comp is not None, "Stream is closed"
        out = self._comp.flush()
        if out:
            self._raw.write(out)
        self._comp = zstd.ZstdCompressor(level=level)

    def close(self) -> None:
        if not self.closed:
            if self._comp is not None:
                out = self._comp.flush()
                if out:
                    self._raw.write(out)
                self._comp = None
            super().close()


class TechnicalDump:
    """
    Produce a PostgreSQL COPY-based dump of all database rows belonging to a single project
    and its vault images, packaged as a zstd-compressed tar archive (.tar.zst).
    """

    DB_ZSTD_LEVEL: int = zstd.COMPRESSION_LEVEL_DEFAULT
    VAULT_ZSTD_LEVEL: int = -5
    IMAGES_REPORT_INTERVAL_SECONDS: float = 5.0

    def __init__(
        self,
        project_id: ProjectIDT,
        vault_dir: str,
    ):
        self.project_id: ProjectIDT = int(project_id)
        self.vault_dir = vault_dir
        self._log_prefix: str = f"Dumping {self.project_id}: "

    @staticmethod
    def archive_filename(project_id: ProjectIDT) -> str:
        now = DateTime.now_time()
        return f"export__TEK_{project_id}_{now.strftime('%Y%m%d_%H%M')}.tar.zst"

    _EXPORT_MODELS: Tuple[Any, ...] = tuple(cfg.model for cfg in TABLE_DUMP_CONFIGS)
    _MODEL_BY_TABLE: Dict[str, Any] = {
        cfg.table_name: cfg.model for cfg in TABLE_DUMP_CONFIGS
    }

    @staticmethod
    def _model_columns(model: Any) -> List[str]:
        return [col.name for col in model.__table__.columns]

    @staticmethod
    def _quoted_columns(model: Any, alias: Optional[str] = None) -> str:
        prefix = f"{alias}." if alias else ""
        return ", ".join(f'{prefix}"{col.name}"' for col in model.__table__.columns)

    @staticmethod
    def _table_queries(projid: int) -> List[Tuple[str, str]]:
        """
        Return ordered (table_name, select_sql) pairs in FK dependency order
        for restoring a single project.
        """
        qcols = TechnicalDump._quoted_columns
        acq_sub = (
            f"SELECT acquisid FROM {Acquisition.__tablename__} "
            f"WHERE acquisid <@ acq_in_prj({projid}) "
            f"AND acq_sample_id IN (SELECT sampleid FROM {Sample.__tablename__} WHERE projid = {projid})"
        )
        obj_sub = (
            f"SELECT objid FROM {ObjectHeader.__tablename__} "
            f"WHERE objid <@ obj_in_prj({projid}) "
            f"AND acquisid IN ({acq_sub})"
        )
        coll_sub = (
            f"SELECT collection_id FROM {CollectionProject.__tablename__} WHERE project_id = {projid} "
            f"UNION "
            f"SELECT collection_id FROM {TaxoRecast.__tablename__} WHERE project_id = {projid}"
        )
        training_where = (
            f"projid = {projid} "
            f"OR training_id IN ("
            f"SELECT DISTINCT training_id FROM {Prediction.__tablename__} WHERE object_id <@ obj_in_prj({projid})"
            f") "
            f"OR training_id IN ("
            f"SELECT DISTINCT training_id FROM {PredictionHisto.__tablename__} WHERE object_id <@ obj_in_prj({projid})"
            f")"
        )
        users_sub = (
            f"SELECT member FROM {ProjectPrivilege.__tablename__} WHERE projid = {projid} "
            f"UNION "
            f"SELECT user_id FROM {UserPreferences.__tablename__} WHERE project_id = {projid} "
            f"UNION "
            f"SELECT training_author FROM {Training.__tablename__} WHERE {training_where} "
            f"UNION "
            f"SELECT classif_who FROM {ObjectHeader.__tablename__} "
            f"WHERE objid <@ obj_in_prj({projid}) AND acquisid IN ({acq_sub}) AND classif_who IS NOT NULL "
            f"UNION "
            f"SELECT classif_who FROM {ObjectsClassifHisto.__tablename__} "
            f"WHERE objid <@ obj_in_prj({projid}) AND classif_who IS NOT NULL "
            f"UNION "
            f"SELECT provider_user_id FROM {Collection.__tablename__} "
            f"WHERE id IN ({coll_sub}) AND provider_user_id IS NOT NULL "
            f"UNION "
            f"SELECT contact_user_id FROM {Collection.__tablename__} "
            f"WHERE id IN ({coll_sub}) AND contact_user_id IS NOT NULL"
        )
        taxo_seed_sub = (
            f"SELECT classif_id FROM {ObjectHeader.__tablename__} "
            f"WHERE objid <@ obj_in_prj({projid}) AND acquisid IN ({acq_sub}) AND classif_id IS NOT NULL "
            f"UNION "
            f"SELECT classif_id FROM {ObjectsClassifHisto.__tablename__} "
            f"WHERE objid <@ obj_in_prj({projid}) AND classif_id IS NOT NULL "
            f"UNION "
            f"SELECT classif_id FROM {Prediction.__tablename__} "
            f"WHERE object_id <@ obj_in_prj({projid}) AND classif_id IS NOT NULL "
            f"UNION "
            f"SELECT classif_id FROM {PredictionHisto.__tablename__} "
            f"WHERE object_id <@ obj_in_prj({projid}) AND classif_id IS NOT NULL "
            f"UNION "
            f"SELECT id FROM {ProjectTaxoStat.__tablename__} WHERE projid = {projid}"
        )
        return [
            (
                Instrument.__tablename__,
                f"SELECT {qcols(Instrument)} FROM {Instrument.__tablename__} "
                f"WHERE instrument_id IN (SELECT instrument_id FROM {Project.__tablename__} WHERE projid = {projid})",
            ),
            (
                Organization.__tablename__,
                f"SELECT {qcols(Organization)} FROM {Organization.__tablename__} "
                f"WHERE id IN (SELECT organization_id FROM {User.__tablename__} WHERE id IN ({users_sub}) AND organization_id IS NOT NULL)",
            ),
            (
                User.__tablename__,
                f"SELECT {qcols(User)} FROM {User.__tablename__} WHERE id IN ({users_sub})",
            ),
            (
                Taxonomy.__tablename__,
                f"WITH RECURSIVE _taxo_tree AS ("
                f"SELECT {qcols(Taxonomy)} FROM {Taxonomy.__tablename__} WHERE id IN ({taxo_seed_sub}) "
                f"UNION "
                f"SELECT {qcols(Taxonomy, alias='t')} FROM {Taxonomy.__tablename__} t "
                f"JOIN _taxo_tree tt ON t.id = tt.parent_id OR t.id = tt.rename_to"
                f") SELECT {qcols(Taxonomy)} FROM _taxo_tree",
            ),
            (
                Collection.__tablename__,
                f"SELECT {qcols(Collection)} FROM {Collection.__tablename__} WHERE id IN ({coll_sub})",
            ),
            (
                Project.__tablename__,
                f"SELECT {qcols(Project)} FROM {Project.__tablename__} WHERE projid = {projid}",
            ),
            (
                ProjectPrivilege.__tablename__,
                f"SELECT {qcols(ProjectPrivilege)} FROM {ProjectPrivilege.__tablename__} WHERE projid = {projid}",
            ),
            (
                ProjectTaxoStat.__tablename__,
                f"SELECT {qcols(ProjectTaxoStat)} FROM {ProjectTaxoStat.__tablename__} WHERE projid = {projid}",
            ),
            (
                ProjectVariables.__tablename__,
                f"SELECT {qcols(ProjectVariables)} FROM {ProjectVariables.__tablename__} WHERE project_id = {projid}",
            ),
            (
                TaxoRecast.__tablename__,
                f"SELECT {qcols(TaxoRecast)} FROM {TaxoRecast.__tablename__} WHERE project_id = {projid}",
            ),
            (
                CollectionProject.__tablename__,
                f"SELECT {qcols(CollectionProject)} FROM {CollectionProject.__tablename__} WHERE project_id = {projid}",
            ),
            (
                UserPreferences.__tablename__,
                f"SELECT {qcols(UserPreferences)} FROM {UserPreferences.__tablename__} WHERE project_id = {projid}",
            ),
            (
                Training.__tablename__,
                f"SELECT {qcols(Training)} FROM {Training.__tablename__} "
                f"WHERE projid = {projid} "
                f"OR training_id IN ("
                f"SELECT DISTINCT training_id FROM {Prediction.__tablename__} WHERE object_id <@ obj_in_prj({projid})"
                f") "
                f"OR training_id IN ("
                f"SELECT DISTINCT training_id FROM {PredictionHisto.__tablename__} WHERE object_id <@ obj_in_prj({projid})"
                f")",
            ),
            (
                Sample.__tablename__,
                f"SELECT {qcols(Sample)} FROM {Sample.__tablename__} WHERE projid = {projid}",
            ),
            (
                Acquisition.__tablename__,
                f"SELECT {qcols(Acquisition)} FROM {Acquisition.__tablename__} "
                f"WHERE acquisid <@ acq_in_prj({projid}) "
                f"AND acq_sample_id IN (SELECT sampleid FROM {Sample.__tablename__} WHERE projid = {projid})",
            ),
            (
                Process.__tablename__,
                f"SELECT {qcols(Process)} FROM {Process.__tablename__} WHERE processid IN ({acq_sub})",
            ),
            (
                ObjectHeader.__tablename__,
                f"SELECT {qcols(ObjectHeader)} FROM {ObjectHeader.__tablename__} "
                f"WHERE objid <@ obj_in_prj({projid}) "
                f"AND acquisid IN ({acq_sub})",
            ),
            (
                ObjectFields.__tablename__,
                f"SELECT {qcols(ObjectFields)} FROM {ObjectFields.__tablename__} "
                f"WHERE objfid <@ obj_in_prj({projid}) "
                f"AND objfid IN ({obj_sub})",
            ),
            (
                Image.__tablename__,
                f"SELECT {qcols(Image)} FROM {Image.__tablename__} "
                f"WHERE objid <@ obj_in_prj({projid}) "
                f"AND objid IN ({obj_sub})",
            ),
            (
                ImageFile.__tablename__,
                f"SELECT DISTINCT {qcols(ImageFile, alias='imf')} FROM {ImageFile.__tablename__} imf "
                f"JOIN {Image.__tablename__} img ON img.imgid = imf.imgid "
                f"WHERE img.objid <@ obj_in_prj({projid})",
            ),
            (
                ObjectsClassifHisto.__tablename__,
                f"SELECT {qcols(ObjectsClassifHisto)} FROM {ObjectsClassifHisto.__tablename__} WHERE objid <@ obj_in_prj({projid})",
            ),
            (
                ObjectCNNFeatureVector.__tablename__,
                f"SELECT {qcols(ObjectCNNFeatureVector)} FROM {ObjectCNNFeatureVector.__tablename__} WHERE objcnnid <@ obj_in_prj({projid})",
            ),
            (
                Prediction.__tablename__,
                f"SELECT {qcols(Prediction)} FROM {Prediction.__tablename__} WHERE object_id <@ obj_in_prj({projid})",
            ),
            (
                PredictionHisto.__tablename__,
                f"SELECT {qcols(PredictionHisto)} FROM {PredictionHisto.__tablename__} WHERE object_id <@ obj_in_prj({projid})",
            ),
        ]

    def _collect_schema_metadata(
        self, cur: Any, queries: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """
        Collect PostgreSQL schema metadata for all exported tables in dependency order.
        """
        table_columns = [
            (table_name, self._model_columns(self._MODEL_BY_TABLE[table_name]))
            for table_name, _select_sql in queries
        ]
        return build_schema_metadata(cur, self.project_id, table_columns)

    def _spool_vault_image_rows(
        self, raw_conn: Any, image_rows_file: IO[str]
    ) -> None:
        """
        Write the project's image rows to ``image_rows_file`` as JSON lines.

        Must be called inside the dump transaction so that the list of vault
        files matches the exported ``images`` table rows.
        """
        sql = (
            "SELECT img.imgid, img.orig_file_name, img.thumb_height "
            "FROM images img "
            "WHERE img.objid <@ obj_in_prj(%s) "
            "ORDER BY img.imgid"
        )
        with raw_conn.cursor(name="vault_images") as cur:
            cur.itersize = SQL.DB_CHUNK_SIZE * 10
            cur.execute(sql, (self.project_id,))
            for imgid, orig_file_name, thumb_height in cur:
                image_rows_file.write(
                    json.dumps([imgid, orig_file_name, thumb_height]) + "\n"
                )

    def _copy_vault_images(
        self,
        tfile: tarfile.TarFile,
        image_rows_file: IO[str],
        progress_start: int = 75,
        progress_end: int = 95,
        progress_cb: Optional[ProgressCallback] = None,
        total_image_rows: int = 0,
    ) -> None:
        """
        Copy project images and thumbnails from the Vault into the tar archive under vault/.

        ``image_rows_file`` is a text stream of JSON lines (imgid, orig_file_name,
        thumb_height), spooled from the same DB snapshot as the table dump.
        """
        logger.info(
            "%sCopying vault images (%d image rows)",
            self._log_prefix,
            total_image_rows,
        )
        if progress_cb is not None:
            progress_cb(progress_start, "Copying vault images")
        vault = Vault(self.vault_dir)
        added = 0
        last_report_at = time.monotonic()
        last_reported_pct = -1
        for row_idx, line in enumerate(image_rows_file, start=1):
            imgid, orig_file_name, thumb_height = json.loads(line)
            sub_path = Image.img_from_id_and_orig(imgid, orig_file_name)
            img_path = Path(vault.image_path(sub_path))
            if img_path.exists():
                tfile.add(img_path, arcname=f"vault/{sub_path}")
                added += 1
            thumb_sub = Image.thumb_img_from_id_if_there(imgid, thumb_height)
            if thumb_sub is not None:
                thumb_path = Path(vault.image_path(thumb_sub))
                if thumb_path.exists():
                    tfile.add(thumb_path, arcname=f"vault/{thumb_sub}")
                    added += 1
            now = time.monotonic()
            if now - last_report_at >= self.IMAGES_REPORT_INTERVAL_SECONDS:
                last_report_at = now
                if total_image_rows > 0:
                    msg = (
                        f"Copied {added} vault files "
                        f"({row_idx}/{total_image_rows} image rows)"
                    )
                    pct = progress_start + int(
                        (progress_end - progress_start)
                        * min(row_idx, total_image_rows)
                        / total_image_rows
                    )
                else:
                    msg = f"Copied {added} vault files ({row_idx} image rows)"
                    pct = progress_start
                logger.info("%s%s", self._log_prefix, msg)
                if progress_cb is not None:
                    progress_cb(pct, msg)
                    last_reported_pct = pct
        logger.info("%sCopied %d vault files", self._log_prefix, added)
        if progress_cb is not None and last_reported_pct != progress_end:
            progress_cb(progress_end, f"Copied {added} vault files")

    @staticmethod
    def _add_bytes_to_tar(tfile: tarfile.TarFile, name: str, data: bytes) -> None:
        info = tarfile.TarInfo(name=name)
        info.size = len(data)
        tfile.addfile(info, io.BytesIO(data))

    @staticmethod
    def _dump_single_table(
        tfile: tarfile.TarFile,
        cur: Any,
        copy_filename: str,
        select_sql: str,
    ) -> int:
        rows_in_table = 0
        with tempfile.SpooledTemporaryFile(max_size=16 * 1024 * 1024) as tmp:
            with cur.copy(f"COPY ({select_sql}) TO STDOUT") as copy:
                for chunk in copy:
                    chunk_bytes = bytes(chunk)
                    rows_in_table += chunk_bytes.count(b"\n")
                    tmp.write(chunk_bytes)
            size = tmp.tell()
            tmp.seek(0)
            info = tarfile.TarInfo(name=copy_filename)
            info.size = size
            tfile.addfile(info, tmp)
        return rows_in_table

    def _dump_tables_and_metadata(
        self,
        tfile: tarfile.TarFile,
        queries: List[Tuple[str, str]],
        progress_start: int,
        progress_end: int,
        progress_cb: Optional[ProgressCallback],
        vault_image_rows: IO[str],
    ) -> Dict[str, int]:
        total_tables = len(queries)
        row_counts: Dict[str, int] = {}
        restore_lines: List[str] = [
            f"-- Technical project dump for projid={self.project_id}",
            "-- Includes referenced rows from instrument, organizations, users, taxonomy, and collection.",
            "-- Run with: psql -v ON_ERROR_STOP=1 -f restore.sql",
        ]

        # A single REPEATABLE READ transaction guarantees that all table COPYs,
        # the schema metadata and the vault image list come from the same
        # snapshot (i.e. form a consistent archive).
        with Connection.get_raw_psycopg_connection(
            read_only=True, isolation_level=IsolationLevel.REPEATABLE_READ
        ) as raw_conn:
            try:
                with raw_conn.cursor() as cur:
                    metadata = self._collect_schema_metadata(cur, queries)
                    meta_bytes = (
                        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
                    ).encode("utf-8")
                    self._add_bytes_to_tar(tfile, "0_metadata.json", meta_bytes)

                    for idx, (table_name, select_sql) in enumerate(queries, start=1):
                        if progress_cb is not None:
                            pct = progress_start + int(
                                (progress_end - progress_start)
                                * (idx - 1)
                                / total_tables
                            )
                            progress_cb(pct, f"Dumping table {table_name}")
                        copy_filename = f"{idx:02d}_{table_name}.copy"
                        rows_in_table = self._dump_single_table(
                            tfile, cur, copy_filename, select_sql
                        )
                        row_counts[table_name] = rows_in_table
                        quoted_cols = self._quoted_columns(
                            self._MODEL_BY_TABLE[table_name]
                        )
                        restore_lines.append(
                            f"\\copy {table_name} ({quoted_cols}) FROM '{copy_filename}'"
                        )
                        logger.info(
                            "%sDumped %d rows from %s into %s",
                            self._log_prefix,
                            rows_in_table,
                            table_name,
                            copy_filename,
                        )

                    # Spool the vault image list while still in the snapshot
                    # transaction, but before the (slow) filesystem copy.
                    self._spool_vault_image_rows(raw_conn, vault_image_rows)
            finally:
                raw_conn.rollback()

        restore_bytes = ("\n".join(restore_lines) + "\n").encode("utf-8")
        self._add_bytes_to_tar(tfile, "restore.sql", restore_bytes)
        return row_counts

    @staticmethod
    def _add_extra_files(
        tfile: tarfile.TarFile,
        extra_files: Optional[List[Tuple[Path, str]]],
    ) -> None:
        if not extra_files:
            return
        for src_path, arcname in extra_files:
            if src_path.exists():
                tfile.add(src_path, arcname=arcname)

    def dump_project(
        self,
        archive_path: Path,
        progress_start: int = 1,
        progress_end: int = 95,
        progress_cb: Optional[ProgressCallback] = None,
        extra_files: Optional[List[Tuple[Path, str]]] = None,
    ) -> Dict[str, int]:
        """
        Dump all project-scoped tables via PostgreSQL COPY TO STDOUT and vault images into archive_path (.tar.zst).
        Returns a mapping of table_name -> exported row count.
        """
        progress_cb = dedup_progress_cb(progress_cb)
        started_at = time.monotonic()
        queries = self._table_queries(self.project_id)
        db_progress_end = progress_end - 20

        with (
            open(archive_path, "wb") as out_stream,
            _PhasedZstdStream(out_stream, level=self.DB_ZSTD_LEVEL) as zstream,
            tarfile.open(fileobj=zstream, mode="w|") as tfile,
            tempfile.SpooledTemporaryFile(
                max_size=16 * 1024 * 1024, mode="w+", encoding="utf-8"
            ) as vault_image_rows,
        ):
            row_counts = self._dump_tables_and_metadata(
                tfile,
                queries,
                progress_start=progress_start,
                progress_end=db_progress_end,
                progress_cb=progress_cb,
                vault_image_rows=vault_image_rows,
            )

            # Switch to fast compression for already-compressed Vault images.
            zstream.switch_level(self.VAULT_ZSTD_LEVEL)

            # The DB connection is now closed; copy vault files from the
            # image rows spooled within the dump snapshot.
            vault_image_rows.seek(0)
            self._copy_vault_images(
                tfile,
                vault_image_rows,
                progress_start=db_progress_end,
                progress_end=progress_end,
                progress_cb=progress_cb,
                total_image_rows=row_counts.get(Image.__tablename__, 0),
            )

            self._add_extra_files(tfile, extra_files)

        logger.info(
            "%sFinished dump (%d total rows in %.1fs)",
            self._log_prefix,
            sum(row_counts.values()),
            time.monotonic() - started_at,
        )
        return row_counts
