from DB.helpers.SQL import *


def test_sql_wrap(config, database, fastapi, caplog):
    where = WhereClause()
    where *= "obh.classif_id = any (:taxo)"
    where *= "obh.latitude between :MapS and :MapN"
    where *= "obh.n57 >= :freenumst"
    where *= "obh.n57 >= obh.n56"
    where *= "obf.orig_id = :img"
    assert where.referenced_columns(with_prefices=False) == {"classif_id", "latitude", "n57", "n56", "orig_id"}
    assert where.referenced_columns(with_prefices=True) == {'obh.latitude', 'obh.n57', 'obh.classif_id', 'obf.orig_id',
                                                            'obh.n56'}
