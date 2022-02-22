# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# While querying in manual classification page, the longest queries are due to sort.
# Querying a free column for display is not so expensive, as there is a maximum of 1000 obj_field rows read.
# But _sorting_ on one of these columns, one needs to read the whole set of obj_field rows, just to have
# the value for sorting.
#
# The idea here is to setup a sub-DB in sqlite format, containing only the sort column values.
#
import re
from decimal import Decimal
from sqlite3 import OperationalError, Cursor, ProgrammingError
from threading import Thread
from typing import Optional, Tuple, List, Dict, Set, Any

from BO.Mappings import TableMapping
from BO.Project import ProjectBO
from DB import Project
from DB.Project import ProjectIDT
from DB.helpers import Result, Session
from DB.helpers.Connection import Connection
from DB.helpers.SQL import OrderClause, WhereClause
from FS.helpers.SQLite import DBMeta, SQLite3, SQLiteConnection
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

logger = get_logger(__name__)

#
# TODO: Once used, remove the ignore in tox.ini
#

# noinspection SqlDialectInspection,SqlResolve
class ObjectCache(object): # pragma: no cover
    """
        The cache, in read-only mode.
    """
    LOCKER_SQLITE_TBL = "locker"
    SQLITE_FIELDS_TBL = "feature"  # This one seldom changes
    SQLITE_OBJ_TBL = "object"  # This one changes more often

    def __init__(self, project: Project, mapping: TableMapping,
                 where_clause: WhereClause, order_clause: Optional[OrderClause],
                 params: Dict[str, Any], window_start: Optional[int], window_size: Optional[int]):
        self.sort_fields = ProjectBO.get_sort_db_columns(project, mapping=mapping)
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
        return "/tmp/prj_%d_cache.db" % projid

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
        elif self.SQLITE_FIELDS_TBL not in self.meta.tables:
            ret = False, "No cache table"
        elif self.pg_order is None:
            ret = False, "No order"
        else:
            features_meta = self.meta.tables[self.SQLITE_FIELDS_TBL]
            objects_meta = self.meta.tables[self.SQLITE_OBJ_TBL]
            cached_cols = {"obh." + a_col.name for a_col in objects_meta.columns} \
                .union({"obf." + a_col.name for a_col in features_meta.columns})
            oc_refs = self.pg_order.referenced_columns()
            in_order_not_in_cache = set(oc_refs).difference(cached_cols)
            if len(in_order_not_in_cache) > 0:
                # Order clause is simple and 100% compatible b/w DB brands.
                ret = False, "Some column(s) in ORDER not in cache: %s" % in_order_not_in_cache
            else:
                # Where clause is a bit more tricky
                ret = self.try_sqlite_ize(self.pg_where, cached_cols, self.pg_params)
        self.can = ret
        return ret

    def try_sqlite_ize(self, where_clause: WhereClause, cached_cols: Set[str], params: Dict):
        """
            See if where_clause can become an equivalent SQLite one.
            We need the same data & semantic equivalence
        """
        for an_and, its_refs in where_clause.conds_and_refs():
            if its_refs.issubset(cached_cols):
                if "= ANY" in an_and:
                    an_and = an_and.replace("= ANY", "IN (SELECT value FROM json_each") + ")"
                elif "ILIKE" in an_and:
                    an_and = an_and.replace("ILIKE", "LIKE")
                self.cache_where *= an_and
            else:
                ret = False, "Condition in WHERE not in cache: %s (%s)" % (an_and, its_refs)
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

    def _from(self):
        refs_sql = self.cache_where.get_sql() + self.pg_order.get_sql()
        if "obh." in refs_sql and "obf." in refs_sql:
            return ("SELECT objid FROM %s obh JOIN %s obf ON obf.objfid = obh.objid" %
                    (self.SQLITE_OBJ_TBL, self.SQLITE_FIELDS_TBL))
        elif "obf." in refs_sql:
            return "SELECT objfid FROM %s obf " % self.SQLITE_FIELDS_TBL
        return "SELECT objid FROM %s obh" % self.SQLITE_OBJ_TBL

    def pump_cache(self) -> \
            Tuple[Optional[List[int]], Optional[int]]:
        ok, why = self._can_accelerate()
        if not ok:
            logger.info("Not using cache because %s", why)
            return None, None
        return self._fetch(), self._count()

    def _fetch(self):
        # noinspection SqlResolve
        where_sql = self.cache_where.get_sql()
        read_sql = self._from() + " %s %s LIMIT %d OFFSET %d" % (
            where_sql, self.pg_order.get_sql(), self.pg_window_size, self.pg_window_start)
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
        select_sql = re.sub("objf?id", "COUNT(1)", self._from(), 1)
        read_sql = select_sql + where_sql
        try:
            with CodeTimer("SQLite count using '%s':" % read_sql, logger):
                assert self.conn
                res: Cursor = self.conn.execute(read_sql, self.where_params)
                cnt, = res.fetchone()
                res.close()
            return cnt
        except (OperationalError, ProgrammingError) as e:
            logger.error("In %s : %s", read_sql, str(e))
        except Exception as ae:
            logger.error(ae.__class__)
        return None


# noinspection SqlDialectInspection
class ObjectCacheWriter(object): # pragma: no cover
    """
        The cache, in write mode
    """

    def __init__(self, cache: ObjectCache):
        self.projid = cache.projid
        # Select the free columns for the full project
        sort_feature_col = ""
        if len(cache.sort_fields) > 0:
            sort_feature_col = "," + ", ".join(cache.sort_fields)
        self.feature_sql = " SELECT objid AS objfid %s " % sort_feature_col + \
                           " FROM objects WHERE projid = %d" % self.projid
        self.object_sql = " SELECT objid, classif_id, classif_qual " \
                          " FROM objects WHERE projid = %d" % self.projid

    def bg_fetch_fill(self, pg_conn: Connection):
        thrd = Thread(name="cache fetcher for %d" % self.projid,
                      target=self._fetch_and_write, args=(pg_conn,))
        thrd.start()
        thrd.join()

    def _fetch_and_write(self, pg_conn: Connection):
        logger.info("BG cache thread starting")
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
            nb_obj_rows = self.query_pg_and_cache(ObjectCache.SQLITE_OBJ_TBL, pg_sess, self.object_sql)
            nb_feat_rows = self.query_pg_and_cache(ObjectCache.SQLITE_FIELDS_TBL, pg_sess, self.feature_sql)
        except OperationalError as e:
            if "table %s already exists" % ObjectCache.LOCKER_SQLITE_TBL in str(e):
                logger.info("%d locker table exists" % self.projid)
            elif "database is locked" in str(e):
                logger.info("%d db is locked" % self.projid)
            else:
                logger.exception(e)
            return
        finally:
            if locker_present:
                self.conn.execute("vacuum")
                self.conn.execute("drop table %s" % ObjectCache.LOCKER_SQLITE_TBL)
            pg_sess.close()
            self.conn.close()
        logger.info("BG cache thread on %d done. %d and %d rows", self.projid, nb_feat_rows, nb_obj_rows)

    def query_pg_and_cache(self, table_name: str, pg_sess: Session, cache_sql: str) -> int:
        logger.info("For cache fetch: %s", cache_sql)
        res: Result = pg_sess.execute(cache_sql)
        tbl_cols = self.create_sqlite_table(table_name, res)
        nb_ins = self.pg_to_sqlite(table_name, tbl_cols, res)
        return nb_ins

    def pg_to_sqlite(self, table_name: str, table_cols: List[str], res: Result) -> int:
        ins_sql = "INSERT INTO %s (%s) VALUES (%s)" \
                  % (table_name, ",".join([a_col for a_col in table_cols]), ",".join("?" * len(table_cols)))
        nb_ins = 0
        res_arr = []
        for rec in res:
            nb_ins += 1
            # SQLite allows mixed vals so let's turn to int everything possible
            # sqlite_rec = tuple([int(val) if (isinstance(val, float) and int(val) == val) else val
            #                     for val in rec._data])
            # res_arr.append(sqlite_rec)
            # TODO: It looked useless on a benchmark, exact same size of DB file
            res_arr.append(rec._data)
            if nb_ins % 1024 == 0:
                self.conn.executemany(ins_sql, res_arr)
                res_arr.clear()
        else:
            self.conn.executemany(ins_sql, res_arr)
        self.conn.commit()
        return nb_ins

    # https://www.sqlite.org/datatype3.html
    PG_TO_SQLITE = {20: 'INTEGER',  # PG bigint
                    23: 'INTEGER',  # PG integer
                    701: 'REAL',  # PG double
                    1042: 'TEXT',  # PG char
                    1043: 'TEXT'  # PG varchar
                    }

    def create_sqlite_table(self, table_name: str, res: Result) -> List[str]:
        # Create the table from resultset structure & content
        # noinspection PyUnresolvedReferences
        col_descs = res.cursor.description
        sqlite_cols: List[str] = []
        ret: List[str] = []
        for a_desc in col_descs:
            pg_type = a_desc.type_code
            sqlite_type = self.PG_TO_SQLITE[pg_type]
            col_name = a_desc.name
            # First column is PK per convention and usage
            sqlite_col = "%s %s %s" % (col_name, sqlite_type, "PRIMARY KEY" if not ret else "")
            ret.append(col_name)
            sqlite_cols.append(sqlite_col)
        create_table = "CREATE TABLE %s (" % table_name + ",".join(sqlite_cols) + ")"
        self.conn.execute(create_table)
        for a_col in ret[1:]:
            # Index all columns but PK of course
            self.conn.execute("CREATE INDEX %s_%s ON %s (%s)" %
                              (table_name, a_col, table_name, a_col))
        return ret


# noinspection SqlDialectInspection,SqlResolve
class ObjectCacheUpdater(object): # pragma: no cover
    """
        The cache, in update mode.
    """

    def __init__(self, projid: ProjectIDT):
        self.projid = projid

    def update_objects(self, object_ids: List[int], params: Dict):
        upd_sql = "UPDATE object SET classif_id = :classif_id, classif_qual = :classif_qual" \
                  " WHERE objid IN (SELECT value FROM json_each(:obj_ids))"
        params["obj_ids"] = str(object_ids)
        try:
            self._safe_update(upd_sql, params)
        except Exception as e:
            # TODO: Several kinds of error here. File not exists is OK, while a problem
            # during write means that the whole DB is out of sync and thus should be wiped
            logger.error("Cache updater excepts: %s while executing '%s'", str(e), upd_sql)

    def _safe_update(self, upd_sql: str, params: Dict):
        file_name = ObjectCache.file_name(self.projid)
        conn = SQLite3.get_conn(file_name, "rw")  # No create!
        try:
            with CodeTimer("SQLite update using '%s':" % upd_sql, logger):
                conn.execute(upd_sql, params)
                conn.commit()
        finally:
            conn.close()
