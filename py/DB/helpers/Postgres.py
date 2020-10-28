# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# DB utils around PG.
#
from datetime import datetime
from enum import Enum
from typing import List

from sqlalchemy.orm import Session


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
