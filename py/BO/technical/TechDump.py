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
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

from DB.Image import Image
from DB.Project import ProjectIDT
from DB.helpers import SQL, Session
from DB.helpers.Direct import text
from FS.Vault import Vault
from helpers import DateTime
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)

ProgressCallback = Callable[[int, str], None]


class _StreamingSink(io.RawIOBase):
    """Non-seekable writable stream that buffers chunks for incremental yielding."""

    def __init__(self) -> None:
        self._chunks: List[bytes] = []
        self._pos: int = 0

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def tell(self) -> int:
        return self._pos

    def write(self, b: Any) -> int:
        data = bytes(b)
        if data:
            self._chunks.append(data)
            self._pos += len(data)
        return len(data)

    def drain(self) -> bytes:
        if not self._chunks:
            return b""
        out = b"".join(self._chunks)
        self._chunks.clear()
        return out


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

    @staticmethod
    def _table_queries(projid: int) -> List[Tuple[str, str]]:
        """
        Return ordered (table_name, select_sql) pairs in FK dependency order
        for restoring a single project.
        """
        acq_sub = (
            f"SELECT acquisid FROM acquisitions "
            f"WHERE acquisid <@ acq_in_prj({projid}) "
            f"AND acq_sample_id IN (SELECT sampleid FROM samples WHERE projid = {projid})"
        )
        obj_sub = (
            f"SELECT objid FROM obj_head "
            f"WHERE objid <@ obj_in_prj({projid}) "
            f"AND acquisid IN ({acq_sub})"
        )
        return [
            ("projects", f"SELECT * FROM projects WHERE projid = {projid}"),
            ("projectspriv", f"SELECT * FROM projectspriv WHERE projid = {projid}"),
            (
                "projects_taxo_stat",
                f"SELECT * FROM projects_taxo_stat WHERE projid = {projid}",
            ),
            (
                "projects_variables",
                f"SELECT * FROM projects_variables WHERE project_id = {projid}",
            ),
            (
                "taxo_recast",
                f"SELECT * FROM taxo_recast WHERE project_id = {projid}",
            ),
            (
                "collection_project",
                f"SELECT * FROM collection_project WHERE project_id = {projid}",
            ),
            (
                "user_preferences",
                f"SELECT * FROM user_preferences WHERE project_id = {projid}",
            ),
            (
                "training",
                f"SELECT * FROM training "
                f"WHERE projid = {projid} "
                f"OR training_id IN ("
                f"SELECT DISTINCT training_id FROM prediction WHERE object_id <@ obj_in_prj({projid})"
                f") "
                f"OR training_id IN ("
                f"SELECT DISTINCT training_id FROM prediction_histo WHERE object_id <@ obj_in_prj({projid})"
                f")",
            ),
            ("samples", f"SELECT * FROM samples WHERE projid = {projid}"),
            (
                "acquisitions",
                f"SELECT * FROM acquisitions "
                f"WHERE acquisid <@ acq_in_prj({projid}) "
                f"AND acq_sample_id IN (SELECT sampleid FROM samples WHERE projid = {projid})",
            ),
            ("process", f"SELECT * FROM process WHERE processid IN ({acq_sub})"),
            (
                "obj_head",
                f"SELECT * FROM obj_head "
                f"WHERE objid <@ obj_in_prj({projid}) "
                f"AND acquisid IN ({acq_sub})",
            ),
            (
                "obj_field",
                f"SELECT * FROM obj_field "
                f"WHERE objfid <@ obj_in_prj({projid}) "
                f"AND objfid IN ({obj_sub})",
            ),
            (
                "images",
                f"SELECT * FROM images "
                f"WHERE objid <@ obj_in_prj({projid}) "
                f"AND objid IN ({obj_sub})",
            ),
            (
                "image_file",
                f"SELECT DISTINCT imf.* FROM image_file imf "
                f"JOIN images img ON img.imgid = imf.imgid "
                f"WHERE img.objid <@ obj_in_prj({projid})",
            ),
            (
                "objectsclassifhisto",
                f"SELECT * FROM objectsclassifhisto WHERE objid <@ obj_in_prj({projid})",
            ),
            (
                "obj_cnn_features_vector",
                f"SELECT * FROM obj_cnn_features_vector WHERE objcnnid <@ obj_in_prj({projid})",
            ),
            (
                "prediction",
                f"SELECT * FROM prediction WHERE object_id <@ obj_in_prj({projid})",
            ),
            (
                "prediction_histo",
                f"SELECT * FROM prediction_histo WHERE object_id <@ obj_in_prj({projid})",
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
            columns = [
                {
                    "name": col_name,
                    "type": col_type,
                    "nullable": bool(nullable),
                    "default": col_default,
                }
                for col_name, col_type, nullable, col_default in cur.fetchall()
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

    def _iter_vault_images(
        self,
        tfile: tarfile.TarFile,
        sink: Optional[_StreamingSink] = None,
        progress_start: int = 75,
        progress_end: int = 95,
        progress_cb: Optional[ProgressCallback] = None,
        total_image_rows: int = 0,
    ) -> Iterator[bytes]:
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
                    if sink is not None:
                        data = sink.drain()
                        if data:
                            yield data
                thumb_sub = Image.thumb_img_from_id_if_there(imgid, thumb_height)
                if thumb_sub is not None:
                    thumb_path = Path(vault.image_path(thumb_sub))
                    if thumb_path.exists():
                        tfile.add(thumb_path, arcname=f"vault/{thumb_sub}")
                        added += 1
                        if sink is not None:
                            data = sink.drain()
                            if data:
                                yield data
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

    def _iter_dump_project(
        self,
        dest: Optional[Path] = None,
        sink: Optional[_StreamingSink] = None,
        progress_start: int = 1,
        progress_end: int = 95,
        row_counts: Optional[Dict[str, int]] = None,
        progress_cb: Optional[ProgressCallback] = None,
        extra_files: Optional[List[Tuple[Path, str]]] = None,
    ) -> Iterator[bytes]:
        """
        Dump all project-scoped tables via PostgreSQL COPY TO STDOUT and vault images into a .tar.zst archive.
        When sink is provided, yields compressed .tar.zst byte chunks incrementally.
        """
        started_at = time.monotonic()
        queries = self._table_queries(self.project_id)
        db_progress_end = progress_end - 20
        total_tables = len(queries)
        if row_counts is None:
            row_counts = {}
        restore_lines: List[str] = [
            f"-- Technical project dump for projid={self.project_id}",
            "-- Prerequisite: referenced rows in instrument, taxonomy, users, and collection must exist.",
            "-- Run with: psql -v ON_ERROR_STOP=1 -f restore.sql",
        ]

        sa_conn = self.ro_session.connection()
        raw_conn: Any = sa_conn.connection.driver_connection
        assert raw_conn is not None, "Missing DBAPI driver connection"

        out_ctx: Any = (
            nullcontext(sink) if sink is not None else open(dest, "wb")  # type: ignore[arg-type]
        )
        with out_ctx as out_stream:
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
                        if sink is not None:
                            data = sink.drain()
                            if data:
                                yield data

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
                            if sink is not None:
                                data = sink.drain()
                                if data:
                                    yield data
                            row_counts[table_name] = rows_in_table
                            restore_lines.append(
                                f"\\copy {table_name} FROM '{copy_filename}'"
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
                    if sink is not None:
                        data = sink.drain()
                        if data:
                            yield data

                    yield from self._iter_vault_images(
                        tfile,
                        sink=sink,
                        progress_start=db_progress_end,
                        progress_end=progress_end,
                        progress_cb=progress_cb,
                        total_image_rows=row_counts.get("images", 0),
                    )

                    if extra_files:
                        for src_path, arcname in extra_files:
                            if src_path.exists():
                                tfile.add(src_path, arcname=arcname)

        if sink is not None:
            data = sink.drain()
            if data:
                yield data
        logger.info(
            "%sFinished dump (%d total rows in %.1fs)",
            self._log_prefix,
            sum(row_counts.values()),
            time.monotonic() - started_at,
        )

    def dump_project(
        self,
        archive_path: Path,
        progress_start: int = 1,
        progress_end: int = 95,
        progress_cb: Optional[ProgressCallback] = None,
        extra_files: Optional[List[Tuple[Path, str]]] = None,
    ) -> Dict[str, int]:
        """
        Dump all project-scoped tables via PostgreSQL COPY TO STDOUT into archive_path (.tar.zst).
        Returns a mapping of table_name -> exported row count.
        """
        row_counts: Dict[str, int] = {}
        for _ in self._iter_dump_project(
            dest=archive_path,
            sink=None,
            progress_start=progress_start,
            progress_end=progress_end,
            row_counts=row_counts,
            progress_cb=progress_cb,
            extra_files=extra_files,
        ):
            pass
        return row_counts

    def stream_archive(self) -> Iterator[bytes]:
        """
        Stream the technical project .tar.zst archive incrementally as byte chunks.
        """
        sink = _StreamingSink()
        yield from self._iter_dump_project(
            dest=None, sink=sink, progress_cb=None, extra_files=None
        )
