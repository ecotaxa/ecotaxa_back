# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# DB utils around PG.
#
from datetime import datetime
from enum import Enum
from typing import List, Tuple

# noinspection PyUnresolvedReferences
from sqlalchemy import VARCHAR, INTEGER, CHAR
# noinspection PyUnresolvedReferences
from sqlalchemy.dialects.postgresql import DOUBLE_PRECISION, DATE, TIMESTAMP, BIGINT, BYTEA
# noinspection PyUnresolvedReferences
from sqlalchemy.dialects.postgresql import insert as pg_insert, dialect as pg_dialect

from .ORM import text, Session, column, Integer


def populate(store1, sess, seq_name, size):
    store = store1
    res = sess.execute("select nextval('%s') FROM generate_series(1,%d)" % (seq_name, size))
    for a_num in res:
        store.append(a_num[0])


class SequenceCache(object):
    """
        Generate and keep in memory some valid sequence numbers.
    """

    def __init__(self, session: Session, seq_name: str, size: int):
        self.sess = session
        self.seq_name = seq_name
        self.size = size
        self.store: List[int] = []
        populate(self.store, self.sess, self.seq_name, self.size)

    def next(self):
        try:
            return self.store.pop(0)
        except IndexError:
            populate(self.store, self.sess, self.seq_name, self.size)
            return self.next()


class DateFormat(int, Enum):
    ISO_8601_2004_E = 1  # ISO 8601:2004(E)


def timestamp_to_str(ts: datetime, fmt: int = DateFormat.ISO_8601_2004_E) -> str:
    """
        Convert a postgres timestamp to a string.
        As per DBAPI, it's mapped to a DateTime.
    """
    assert fmt == DateFormat.ISO_8601_2004_E
    # e.g. 2009-02-20T08:40Z as we have UTC dates
    ret = ts.isoformat()
    if len(ret) > 10:
        return ret + "Z"
    else:
        return ret


def values_cte(name: str, cols: Tuple[str, str], values: List[Tuple[int, int]]):
    """
        Return a SQLAlchemy values CTE from given data.
        Example CTE:
            with upd_smp (src_id, dst_id) as (values (5,6), (7,8)),
    :param cols: The column names in the CTE.
    :param values: The constant values.
    """
    # Below generate a union all which is ugly
    # sa=sqlalchemy
    # first_values = sa.select([sa.cast(sa.literal(values[0][0]), sa.Integer).label(cols[0]),
    #                           sa.cast(sa.literal(values[0][1]), sa.Integer).label(cols[1])])
    # stmts = [first_values]
    # stmts.extend([sa.select([sa.literal(a_val[0]), sa.literal(a_val[1])]) for a_val in values[1:]])
    # cte = sa.union_all(*stmts).cte(name=name)
    # return cte

    cte_txt = "values " + ", ".join(["(%d,%d)" % a_val_pair for a_val_pair in values])
    # Giving names to columns is OK in the text but does not propagate to the WITH statement:
    #    vals_text = sa.text(cte_txt).columns(column(cols[0], Integer), column(cols[1], Integer))
    # The columns are named "columnX" by PG
    vals_text = text(cte_txt).columns(column("column1", Integer), column("column2", Integer))
    ret = vals_text.cte(name=name)
    return ret
