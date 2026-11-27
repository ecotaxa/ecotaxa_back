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
from typing import Any, Callable, Dict, List, Optional, Tuple

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
from DB.helpers import SQL, Session
from DB.helpers.Direct import text
from FS.Vault import Vault
from helpers import DateTime
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[int, str], None]


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
        ro_session: Session,
        project_id: ProjectIDT,
        vault_dir: str,
    ):
        self.ro_session = ro_session
        self.project_id: ProjectIDT = int(project_id)
        self.vault_dir = vault_dir
        self._log_prefix: str = f"Dumping {self.project_id}: "

    @staticmethod
    def archive_filename(project_id: ProjectIDT) -> str:
        now = DateTime.now_time()
        return f"export__TEK_{project_id}_{now.strftime('%Y%m%d_%H%M')}.tar.zst"

    _EXPORT_MODELS: Tuple[Any, ...] = (
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
    _MODEL_BY_TABLE: Dict[str, Any] = {
        m.__tablename__: m for m in _EXPORT_MODELS
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
        cur.execute("SELECT version()")
        pg_version_row = cur.fetchone()
        pg_version = pg_version_row[0] if pg_version_row else None

        alembic_version: Optional[str] = None
        cur.execute("SELECT to_regclass('alembic_version')")
        if cur.fetchone()[0] is not None:
            cur.execute("SELECT version_num FROM alembic_version LIMIT 1")
            alembic_row = cur.fetchone()
            if alembic_row is not None:
                alembic_version = alembic_row[0]

        tables_meta: List[Dict[str, Any]] = []
        for idx, (table_name, _select_sql) in enumerate(queries, start=1):
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
            model = self._MODEL_BY_TABLE[table_name]
            columns = [
                pg_cols_by_name[col_name]
                for col_name in self._model_columns(model)
                if col_name in pg_cols_by_name
            ]

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
            primary_key = [row[0] for row in cur.fetchall()]

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
            foreign_keys = [
                {"name": fk_name, "definition": fk_def}
                for fk_name, fk_def in cur.fetchall()
            ]

            tables_meta.append(
                {
                    "name": table_name,
                    "copy_file": f"{idx:02d}_{table_name}.copy",
                    "columns": columns,
                    "primary_key": primary_key,
                    "foreign_keys": foreign_keys,
                }
            )

        return {
            "project_id": self.project_id,
            "exported_at": DateTime.now_time().isoformat(),
            "format": "pg_copy_tar_zst",
            "postgres_version": pg_version,
            "alembic_version": alembic_version,
            "tables": tables_meta,
        }

    def _copy_vault_images(
        self,
        tfile: tarfile.TarFile,
        progress_start: int = 75,
        progress_end: int = 95,
        progress_cb: Optional[ProgressCallback] = None,
        total_image_rows: int = 0,
    ) -> None:
        """
        Copy project images and thumbnails from the Vault into the tar archive under vault/.
        """
        logger.info(
            "%sCopying vault images (%d image rows)",
            self._log_prefix,
            total_image_rows,
        )
        if progress_cb is not None:
            progress_cb(progress_start, "Copying vault images")
        vault = Vault(self.vault_dir)
        sql = text(
            "SELECT img.imgid, img.orig_file_name, img.thumb_height "
            "FROM images img "
            "WHERE img.objid <@ obj_in_prj(:prj) "
            "ORDER BY img.imgid"
        )
        added = 0
        last_report_at = time.monotonic()
        with self.ro_session.execute(
            sql.execution_options(
                stream_results=True, max_row_buffer=SQL.DB_CHUNK_SIZE * 10
            ),
            {"prj": self.project_id},
        ) as res:
            for row_idx, (imgid, orig_file_name, thumb_height) in enumerate(
                res, start=1
            ):
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
        logger.info("%sCopied %d vault files", self._log_prefix, added)
        if progress_cb is not None:
            progress_cb(progress_end, f"Copied {added} vault files")

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
        started_at = time.monotonic()
        queries = self._table_queries(self.project_id)
        db_progress_end = progress_end - 20
        total_tables = len(queries)
        row_counts: Dict[str, int] = {}
        restore_lines: List[str] = [
            f"-- Technical project dump for projid={self.project_id}",
            "-- Includes referenced rows from instrument, organizations, users, taxonomy, and collection.",
            "-- Run with: psql -v ON_ERROR_STOP=1 -f restore.sql",
        ]

        sa_conn = self.ro_session.connection()
        raw_conn: Any = sa_conn.connection.driver_connection
        assert raw_conn is not None, "Missing DBAPI driver connection"

        with open(archive_path, "wb") as out_stream:
            with _PhasedZstdStream(out_stream, level=self.DB_ZSTD_LEVEL) as zstream:
                with tarfile.open(fileobj=zstream, mode="w|") as tfile:
                    with raw_conn.cursor() as cur:
                        metadata = self._collect_schema_metadata(cur, queries)
                        meta_bytes = (
                            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
                        ).encode("utf-8")
                        meta_info = tarfile.TarInfo(name="0_metadata.json")
                        meta_info.size = len(meta_bytes)
                        tfile.addfile(meta_info, io.BytesIO(meta_bytes))

                        for idx, (table_name, select_sql) in enumerate(
                            queries, start=1
                        ):
                            if progress_cb is not None:
                                pct = progress_start + int(
                                    (db_progress_end - progress_start)
                                    * (idx - 1)
                                    / total_tables
                                )
                                progress_cb(pct, f"Dumping table {table_name}")
                            copy_filename = f"{idx:02d}_{table_name}.copy"
                            rows_in_table = 0
                            with tempfile.SpooledTemporaryFile(
                                max_size=16 * 1024 * 1024
                            ) as tmp:
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

                    restore_bytes = ("\n".join(restore_lines) + "\n").encode("utf-8")
                    restore_info = tarfile.TarInfo(name="restore.sql")
                    restore_info.size = len(restore_bytes)
                    tfile.addfile(restore_info, io.BytesIO(restore_bytes))

                    # Switch to fast compression for already-compressed Vault images.
                    zstream.switch_level(self.VAULT_ZSTD_LEVEL)

                    self._copy_vault_images(
                        tfile,
                        progress_start=db_progress_end,
                        progress_end=progress_end,
                        progress_cb=progress_cb,
                        total_image_rows=row_counts.get(Image.__tablename__, 0),
                    )

                    if extra_files:
                        for src_path, arcname in extra_files:
                            if src_path.exists():
                                tfile.add(src_path, arcname=arcname)

        logger.info(
            "%sFinished dump (%d total rows in %.1fs)",
            self._log_prefix,
            sum(row_counts.values()),
            time.monotonic() - started_at,
        )
        return row_counts
