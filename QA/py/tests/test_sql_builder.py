from DB.helpers.SQL import *


def test_sql_wrap(config, database, fastapi, caplog):
    where = WhereClause()
    where *= "obh.classif_id = any (:taxo)"
    where *= "obh.latitude between :MapS and :MapN"
    where *= "obh.n57 >= :freenumst"
    where *= "obh.n57 >= obh.n56"
    where *= "obf.orig_id = :img"
    assert list(where.conds_and_refs()) == [('obh.classif_id = any (:taxo)', {'obh.classif_id'}),
                                            ('obh.latitude between :MapS and :MapN', {'obh.latitude'}),
                                            ('obh.n57 >= :freenumst', {'obh.n57'}),
                                            ('obh.n57 >= obh.n56', {'obh.n56', 'obh.n57'}),
                                            ('obf.orig_id = :img', {'obf.orig_id'})]
