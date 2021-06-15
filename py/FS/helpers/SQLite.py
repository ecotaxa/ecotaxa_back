# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Minimal wrapper over python sqlite3
#
import sqlite3
from dataclasses import dataclass
from sqlite3.dbapi2 import Connection as SQLiteConnection
from typing import List, Dict


@dataclass()
class ColMeta:
    """
        Column metadata.
    """
    name: str


@dataclass()
class TblMeta:
    """
        Table metadata.
    """
    columns: List[ColMeta]

    def parse(self, tbl_sql: str):
        """ e.g CREATE TABLE cache (objfid INTEGER NOT NULL, 01 REAL,n03 REAL,...PRIMARY KEY (objfid)))
        """
        cols = tbl_sql.split("(")[1]
        for a_col in cols.split(","):
            name, *rest = a_col.split()
            self.columns.append(ColMeta(name))
        return self


@dataclass()
class DBMeta:
    """
        DB metadata.
    """
    tables: Dict[str, TblMeta]


class SQLite3(object):

    @staticmethod
    def get_conn(file_name: str, mode: str) -> SQLiteConnection:
        # https://sqlite.org/uri.html#recognized_query_parameters
        uri = "file:" + file_name + "?mode=" + mode
        conn = sqlite3.connect(uri, timeout=0, uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def get_meta(conn: SQLiteConnection) -> DBMeta:
        # noinspection SqlResolve
        stmt = conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master")
        tbls = {}
        for a_row in stmt:
            if a_row['type'] == "table":
                tbls[a_row["name"]] = TblMeta([]).parse(a_row["sql"])
        stmt.close()
        return DBMeta(tbls)
