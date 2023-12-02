# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# While querying in manual classification page, the longest queries are due to sort.
# Querying a free column for display is not so expensive, as there is a maximum of 1000 rows read.
# But _sorting_ on one of these columns, one needs to read the whole set of rows, just to have
# the value from free columns for sorting.
#
# The idea here is to setup a sub-DB in sqlite format, containing only the sort column values.
#
import re
from decimal import Decimal
from os import unlink
from sqlite3 import OperationalError, Cursor, ProgrammingError
from threading import Thread
from typing import Optional, Tuple, List, Dict, Set, Any

from BO.Mappings import TableMapping
from BO.ObjectSet import ObjectIDListT
from BO.Project import ProjectBO
from DB import ObjectHeader
from DB.Project import Project, ProjectIDT
from DB.helpers import Result, Session
from DB.helpers.Connection import Connection
from DB.helpers.Direct import text
from DB.helpers.SQL import OrderClause, WhereClause
from FS.helpers.SQLite import DBMeta, SQLite3, SQLiteConnection
from helpers.DynamicLogs import get_logger, LogsSwitcher, LogEmitter
from helpers.Timer import CodeTimer

logger = get_logger(__name__)


#
# TODO: Once used, remove the ignore in tox.ini
#


# noinspection SqlDialectInspection,SqlResolve
class ObjectCache(LogEmitter):  # pragma: no cover
    """
    The cache, in read-only mode.
    """

    LOCKER_SQLITE_TBL = "locker"
    SQLITE_OBJ_TBL = "object"

    def __init__(
        self,
        project: Project,
        mapping: TableMapping,
        where_clause: WhereClause,
        order_clause: Optional[OrderClause],
        params: Dict[str, Any],
        window_start: Optional[int],
        window_size: Optional[int],
    ):
        super().__init__()
        # Get free column sort possibilities, from project config, e.g. n42, n01
        self.sort_fields = ProjectBO.get_sort_db_columns(project, mapping=mapping)
        self.sort_fields_phy = [
            mapping.phy_lookup(free_col) for free_col in self.sort_fields
        ]
        self.fields_to_phy = {
            col: phy for col, phy in zip(self.sort_fields, self.sort_fields_phy)
        }

        self.projid = project.projid
        # Store the PG query specifics
        self.pg_where = where_clause
        self.pg_order = order_clause
        self.pg_params = params
        self.pg_window_start = window_start
        self.pg_window_size = window_size
        # Move to DBs
        file_name = self.file_name(project.projid)
        self.conn: Optional[SQLiteConnection] = None
        self.meta: Optional[DBMeta] = None
        try:
            self.conn = SQLite3.get_conn(file_name, "ro")
        except OperationalError as e:
            # No file or locked file
            logger.info("No conn %s", str(e))
            return
        try:
            self.meta = SQLite3.get_meta(self.conn)
        except OperationalError as e:
            # DB could be locked e.g. writing
            logger.info("No meta %s", str(e))
            return
        self.can = True, ""
        # The eventual SQLite equivalent, arranged
        self.cache_where = WhereClause()
        self.where_params: Dict[str, Any] = {}

    @staticmethod
    def file_name(projid: int):
        return "/mnt/pgssd1t/sqlite/prj_%d_cache.db" % projid

    def _can_accelerate(self) -> Tuple[bool, str]:
        """
        We can accelerate the query by narrowing 'window_size' objids
        under the following conditions:
         - The cache exists and is usable
         - AND there is a window_size (obviously)
         - AND the order clause columns are all contained in the cache
         - AND ALL filtering criteria are on cached columns
        """
        if self.pg_window_size is None:
            ret = False, "No query window"
        elif self.meta is None:
            ret = False, "No cache DB file"
        elif self.LOCKER_SQLITE_TBL in self.meta.tables:
            ret = False, "Cache being filled"
        elif self.SQLITE_OBJ_TBL not in self.meta.tables:
            ret = False, "No cache 'object' table"
            if self.conn is not None:
                self.conn.close()
            unlink(self.file_name(self.projid))
        elif self.pg_order is None:
            ret = False, "No order"
        else:
            objects_meta = self.meta.tables[self.SQLITE_OBJ_TBL]
            # The cached column, translated in PG form, in order to have comparable sets
            cached_cols = {
                "obh." + a_col.name
                for a_col in objects_meta.columns
                if not a_col.name.startswith("n")
            }.union(
                {
                    ("obf." if self.fields_to_phy[a_col.name][0] else "obh.")
                    + self.fields_to_phy[a_col.name][1]
                    for a_col in objects_meta.columns
                    if a_col.name.startswith("n")
                }
            )
            oc_refs = self.pg_order.referenced_columns()
            oc_refs.discard("obf.objfid")
            in_order_not_in_cache = set(oc_refs).difference(cached_cols)
            if len(in_order_not_in_cache) > 0:
                # Order clause is simple and 100% compatible b/w DB brands.
                ret = (
                    False,
                    "Some column(s) in ORDER not in cache: %s" % in_order_not_in_cache,
                )
            else:
                # Where clause is a bit more tricky
                ret = self.try_sqlite_ize(self.pg_where, cached_cols, self.pg_params)
            self.can = ret
        return ret

    def try_sqlite_ize(
        self, where_clause: WhereClause, cached_cols: Set[str], params: Dict
    ):
        """
        See if where_clause can become an equivalent SQLite one.
        We need the same data & semantic equivalence
        """
        for an_and, its_refs in where_clause.conds_and_refs():
            if its_refs.issubset(cached_cols):
                if "= ANY" in an_and:
                    an_and = (
                        an_and.replace("= ANY", "IN (SELECT value FROM json_each") + ")"
                    )
                elif "ILIKE" in an_and:
                    an_and = an_and.replace("ILIKE", "LIKE")
                self.cache_where *= an_and
            else:
                ret = False, "Condition in WHERE not in cache: %s (%s)" % (
                    an_and,
                    its_refs,
                )
                break
        else:
            ret = True, "With filter"
            self.where_params = self.to_sqlite_params(params)
            # We could save a little time by zero-ing the PG where clause, but this way we have a verification
            # in that users might see unexpected data (and tell...)
            # where_clause.ands.clear()
        return ret

    @staticmethod
    def to_sqlite_params(pg_params):
        """
        Make SQLite params from PG ones. Tightly linked with above try_sqlite_ize and
        the generated SQL in ObjectSet.
        """
        ret = {}
        for a_param, a_val in pg_params.items():
            if isinstance(a_val, Decimal):
                ret[a_param] = float(a_val)
            elif a_param == "taxo":
                ret[a_param] = str(a_val)  # Python->json of list of int is OK
            else:
                ret[a_param] = a_val
        return ret

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def should_refresh(self) -> bool:
        return self.meta is None

    def _from(self) -> str:
        assert self.pg_order is not None
        refs_sql = self.cache_where.get_sql() + self.pg_order.get_sql()
        return "SELECT objid FROM %s obc" % self.SQLITE_OBJ_TBL

    def pump_cache(self) -> Tuple[Optional[List[int]], Optional[int]]:
        with LogsSwitcher(self):
            ok, why = self._can_accelerate()
            if not ok:
                logger.info("%d Not using cache because %s", self.projid, why)
                return None, None
            return self._fetch(), self._count()

    def _fetch(self) -> Optional[ObjectIDListT]:
        assert self.pg_order is not None
        assert self.pg_window_size is not None
        assert self.pg_window_start is not None
        # noinspection SqlResolve
        where_sql = self.cache_where.get_sql()
        order_sql = self.pg_order.get_sql()
        for col, phy in zip(self.sort_fields, self.sort_fields_phy):
            order_sql = order_sql.replace(phy[1], col)
        order_sql = order_sql.replace("obf.objfid", "obh.objid")
        read_sql = self._from() + " %s %s LIMIT %d OFFSET %d" % (
            where_sql,
            order_sql,
            self.pg_window_size,
            self.pg_window_start,
        )
        read_sql = read_sql.replace("obh.", "obc.")
        read_sql = read_sql.replace("obf.", "obc.")
        try:
            with CodeTimer("SQLite read using '%s':" % read_sql, logger):
                assert self.conn
                res: Cursor = self.conn.execute(read_sql, self.where_params)
                # TODO: try fetchmany
                objid_list = [objid for objid, in res]
                res.close()
            return objid_list
        except (OperationalError, ProgrammingError) as e:
            logger.error("In %s : %s", read_sql, str(e))
        except Exception as ae:
            logger.error(ae.__class__)
        return None

    def _count(self) -> Optional[int]:
        # noinspection SqlResolve
        where_sql = self.cache_where.get_sql()
        where_sql = where_sql.replace("obh.", "obc.")
        select_sql = re.sub("objf?id", "COUNT(1)", self._from(), 1)
        read_sql = select_sql + where_sql
        try:
            with CodeTimer("SQLite count using '%s':" % read_sql, logger):
                assert self.conn
                res: Cursor = self.conn.execute(read_sql, self.where_params)
                (cnt,) = res.fetchone()
                res.close()
            return cnt
        except (OperationalError, ProgrammingError) as e:
            logger.error("In %s : %s", read_sql, str(e))
        except Exception as ae:
            logger.error(ae.__class__)
        return None

    def log_file_path(self) -> str:
        return "object_cache.log"


# noinspection SqlDialectInspection
class ObjectCacheWriter(LogEmitter):  # pragma: no cover
    """
    The cache, in write mode
    """

    OBJ_DEFAULT_COLUMNS = ", ".join(  # What is cached in base object
        [
            "obh." + col
            for col in [
                ObjectHeader.objid.name,  # Key
                ObjectHeader.classif_id.name,
                ObjectHeader.classif_qual.name,
                ObjectHeader.orig_id.name,  # Sort column
                ObjectHeader.classif_when.name,  # Sort column
                ObjectHeader.classif_auto_when.name,  # Sort column
            ]
        ]
    )

    def __init__(self, cache: ObjectCache):
        self.projid = cache.projid
        # Select the free columns for the full project
        sort_feature_col = ""
        if len(cache.sort_fields) > 0:
            for col, phy in zip(cache.sort_fields, cache.sort_fields_phy):
                prfx = "obf." if phy[0] else "obh."
                sort_feature_col += ",%s%s as %s" % (prfx, phy[1], col)
        self.object_sql = " SELECT %s %s FROM %s obh" % (
            self.OBJ_DEFAULT_COLUMNS,
            sort_feature_col,
            ObjectHeader.__tablename__,
        )
        if "obf." in self.object_sql:
            self.object_sql += " JOIN obj_field obf ON obf.objfid = obh.objid "
        self.object_sql += (
            " JOIN acquisitions acq ON acq.acquisid = obh.acquisid "
            " JOIN samples sam ON sam.sampleid = acq.acq_sample_id AND sam.projid = %d"
            % self.projid
        )

    def bg_fetch_fill(self, pg_conn: Connection) -> None:
        thrd = Thread(
            name="cache fetcher for %d" % self.projid,
            target=self._logged_fetch_and_write,
            args=(pg_conn,),
        )
        thrd.start()
        thrd.join()

    def _logged_fetch_and_write(self, pg_conn: Connection):
        with LogsSwitcher(self):
            self._fetch_and_write(pg_conn)

    def _fetch_and_write(self, pg_conn: Connection) -> None:
        logger.info("%d BG cache fill thread starting", self.projid)
        file_name = ObjectCache.file_name(self.projid)
        self.conn = SQLite3.get_conn(file_name, "rwc")  # Create if not there
        # Now that the thread has started, we can get a PG session
        pg_sess: Session = pg_conn.get_session()
        locker_present = False
        try:
            self.conn.execute("PRAGMA synchronous=OFF")  # Boost writes
            self.conn.execute("PRAGMA journal=OFF")  # Boost more writes
            # Get a lock on the whole DB
            self.conn.execute("create table %s (foo)" % ObjectCache.LOCKER_SQLITE_TBL)
            locker_present = True
            nb_obj_rows = self.query_pg_and_cache(
                ObjectCache.SQLITE_OBJ_TBL, pg_sess, self.object_sql
            )
        except (OperationalError, ProgrammingError) as e:
            if "table %s already exists" % ObjectCache.LOCKER_SQLITE_TBL in str(e):
                logger.info("%d locker table exists" % self.projid)
            elif "database is locked" in str(e):
                logger.info("%d db is locked" % self.projid)
            else:
                logger.exception(e)
            return
        except Exception as e:
            logger.exception(e)
            return
        finally:
            if locker_present:
                self.conn.execute("vacuum")
                self.conn.execute("drop table %s" % ObjectCache.LOCKER_SQLITE_TBL)
            pg_sess.close()
            self.conn.close()
        logger.info(
            "%d BG cache thread done. %d rows fetched",
            self.projid,
            nb_obj_rows,
        )

    def query_pg_and_cache(
        self, table_name: str, pg_sess: Session, cache_sql: str
    ) -> int:
        logger.info("%d For cache fetch: %s", self.projid, cache_sql)
        res: Result = pg_sess.execute(text(cache_sql))
        tbl_cols = self.create_sqlite_table(table_name, res)
        nb_ins = self.pg_to_sqlite(table_name, tbl_cols, res)
        self.create_sqlite_indexes(table_name, tbl_cols)
        return nb_ins

    def pg_to_sqlite(self, table_name: str, table_cols: List[str], res: Result) -> int:
        ins_sql = "INSERT INTO %s (%s) VALUES (%s)" % (
            table_name,
            ",".join([a_col for a_col in table_cols]),
            ",".join("?" * len(table_cols)),
        )
        nb_ins = 0
        res_arr = []
        for rec in res:
            nb_ins += 1
            res_arr.append(rec._data)
            if nb_ins % 1024 == 0:
                self.conn.executemany(ins_sql, res_arr)
                res_arr.clear()
        else:
            self.conn.executemany(ins_sql, res_arr)
        self.conn.commit()
        return nb_ins

    # https://www.sqlite.org/datatype3.html
    PG_TO_SQLITE = {
        18: "TEXT",  # PG char
        20: "INTEGER",  # PG bigint
        23: "INTEGER",  # PG integer
        701: "REAL",  # PG double
        1114: "TEXT",  # PG datetime # TODO: Rather convert
        1042: "TEXT",  # PG char
        1043: "TEXT",  # PG varchar
    }

    def create_sqlite_table(self, table_name: str, res: Result) -> List[str]:
        # Create the table from resultset structure & content
        col_descs = res.cursor.description  # type:ignore # case5
        sqlite_cols: List[str] = []
        ret: List[str] = []
        for a_desc in col_descs:
            pg_type = a_desc.type_code
            sqlite_type = self.PG_TO_SQLITE[pg_type]
            col_name = a_desc.name
            # First column is PK per convention and usage
            sqlite_col = "%s %s %s" % (
                col_name,
                sqlite_type,
                "PRIMARY KEY" if not ret else "",
            )
            ret.append(col_name)
            sqlite_cols.append(sqlite_col)
        create_table = "CREATE TABLE %s (" % table_name + ",".join(sqlite_cols) + ")"
        self.conn.execute(create_table)
        return ret

    def create_sqlite_indexes(self, table_name: str, columns: List[str]) -> None:
        for a_col in columns[1:]:
            # Index all columns but PK of course
            self.conn.execute(
                "CREATE INDEX %s_%s ON %s (%s)" % (table_name, a_col, table_name, a_col)
            )

    def log_file_path(self) -> str:
        return "object_cache.log"


# noinspection SqlDialectInspection,SqlResolve
class ObjectCacheUpdater(object):  # pragma: no cover
    """
    The cache, in update mode.
    """

    def __init__(self, projid: ProjectIDT):
        self.projid = projid

    def update_objects(self, object_ids: List[int], params: Dict) -> None:
        upd_sql = (
            "UPDATE object SET classif_id = :classif_id, classif_qual = :classif_qual"
            " WHERE objid IN (SELECT value FROM json_each(:obj_ids))"
        )
        params["obj_ids"] = str(object_ids)
        try:
            self._safe_update(upd_sql, params)
        except Exception as e:
            # TODO: Several kinds of error here. File not exists is OK, while a problem
            # during write means that the whole DB is out of sync and thus should be wiped
            logger.error(
                "Cache updater excepts: %s while executing '%s'", str(e), upd_sql
            )

    def _safe_update(self, upd_sql: str, params: Dict):
        file_name = ObjectCache.file_name(self.projid)
        conn = SQLite3.get_conn(file_name, "rw")  # No create!
        try:
            with CodeTimer("SQLite update using '%s':" % upd_sql, logger):
                conn.execute(upd_sql, params)
                conn.commit()
        finally:
            conn.close()
