# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from sqlalchemy.orm import Session


class Bean(dict):
    """
        Holder with just fields & value
    """
    # TODO: A proper subclass with known fields

    # def __init__(self, cols, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.cols = cols

    def __getattr__(self, attr):
        """ To support e.g. obj.latitude """
        return self[attr]

    def __setattr__(self, key, value):
        """ To support e.g. obj.prjid = 1 """
        #assert key in self.cols
        self[key] = value


class SequenceCache(object):
    """
        Generate and keep in memory some valid sequence numbers.
    """

    def __init__(self, session: Session, seq_name: str, size: int):
        self.sess = session
        self.seq_name = seq_name
        self.size = size
        self.store = []
        self.populate()

    def populate(self):
        store = self.store
        res = self.sess.execute("select nextval('%s') FROM generate_series(1,%d)" % (self.seq_name, self.size))
        for a_num in res:
            store.append(a_num[0])

    def next(self):
        try:
            return self.store.pop(0)
        except IndexError:
            self.populate()
            return self.next()
