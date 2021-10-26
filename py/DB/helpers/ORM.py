# -*- coding: utf-8 -*-
# noinspection PyUnresolvedReferences
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Tuple, List, Set, Dict, TypeVar, Type, Any, Union

# noinspection PyUnresolvedReferences
from sqlalchemy import Column, inspect, MetaData, Table, any_ as _pg_any, all_ as _pg_all, not_, and_, or_, func, \
    case, text, select, column, Integer, Float, FLOAT
from sqlalchemy.engine.result import Result  # type: ignore
from sqlalchemy.ext.declarative import declarative_base
# noinspection PyUnresolvedReferences
from sqlalchemy.orm import Query, make_transient, contains_eager, joinedload, subqueryload, selectinload
# For exporting
# noinspection PyUnresolvedReferences
from sqlalchemy.orm import relationship, RelationshipProperty, aliased
# noinspection PyUnresolvedReferences
from sqlalchemy.sql import Delete, Update, Insert, ColumnElement
# noinspection PyUnresolvedReferences
from sqlalchemy.sql.functions import concat

from . import Session

_Base: type = declarative_base()


class Model(_Base):  # type: ignore
    __abstract__ = True  # prevent SQLAlchemy from trying to map
    __tablename__: str
    __table__: Any


# Just forD fun :)
ModelT = Type[Model]

# Generics on some ORM operations
M = TypeVar('M', bound=Model)


def orm_equals(an_obj: Model, another_obj: Model) -> List[str]:
    """
        Compare values of 2 ORM objects, excluding PK and FK.
    """
    ret = []
    to_copy, to_clear = _analyze_cols(an_obj.__table__)
    for a_col in to_copy:
        a_val = getattr(an_obj, a_col)
        another_val = getattr(another_obj, a_col)
        if a_val != another_val:
            ret.append("%s: %s<->%s" % (a_col, str(a_val), str(another_val)))
    return ret


def clone_of(an_obj: M) -> M:
    """
        Return a clone (same class, same plain values) of the ORM-mapped object.
        Keys are not copied, for safety.
        :param an_obj:
        :return:
    """
    table = an_obj.__table__
    ret = an_obj.__class__()
    a_col: Column
    for a_col in table.columns:
        if a_col.primary_key or a_col.foreign_keys:
            continue
        col_name = a_col.name
        val = getattr(an_obj, col_name)
        setattr(ret, col_name, val)
    return ret


def detach_from_session(session: Session, an_orm: M) -> M:
    """
        Detach from the session the given object.
        :param session:
        :param an_orm: A SQLAlchemy produced instance.
        :return:
    """
    if not inspect(an_orm).detached:
        session.expunge(an_orm)
    if an_orm in session:
        make_transient(an_orm)
    return an_orm


def detach_from_session_if(condition: bool, session: Session, an_orm: M) -> M:
    """
        Detach from the session the given object, only if condition is met.
    """
    if condition:
        return detach_from_session(session, an_orm)
    else:
        return an_orm


# key = table name
_table_cache: Dict[Table, Tuple[List[str], List[str]]] = {}


def _analyze_cols(orm_table: Table) -> Tuple[List[str], List[str]]:
    """
        Cache of what to do for cloning, per ORM table.
        :param orm_table:
        :return:
    """
    try:
        return _table_cache[orm_table]
    except KeyError:
        pass
    to_copy = []
    to_clear = []
    a_col: ColumnElement
    for a_col in orm_table.columns:
        if a_col.primary_key or a_col.foreign_keys:
            to_clear.append(a_col.name)
        else:
            to_copy.append(a_col.name)
    _table_cache[orm_table] = (to_copy, to_clear)
    return to_copy, to_clear


def non_key_cols(orm_clazz: ModelT) -> Set[str]:
    """
        Return the columns which are NOT part of any key, thus updatable.
    """
    ok_to_update, _key_cols = _analyze_cols(orm_clazz.__table__)
    return set(ok_to_update)


def minimal_table_of(metadata: MetaData, clazz, to_keep: Set[str], exact_floats=False) -> Table:
    """
        Return a Table, i.e. a SQLAlchemy mapper, with only the given fields.
    :param metadata: SQLAlchemy metadata repository.
    :param clazz: the base mapper class
    :param to_keep: the column (fields) names to keep
    :param exact_floats: if set, FLOAT columns will be returned as Double (exact value)
    :return: new Table
    """
    # Create the ORM clone with PK + mandatory fields + wanted fields
    insp = inspect(clazz)
    cols = []
    a_col: Column
    for a_col in insp.columns:
        if a_col.primary_key or not a_col.nullable or a_col.name in to_keep:
            # noinspection PyProtectedMember
            clone_col = a_col._copy()  # type: ignore
            if exact_floats and isinstance(clone_col.type, FLOAT):
                clone_col.type = Float(asdecimal=True)
            cols.append(clone_col)
    args = [clazz.__tablename__, metadata]
    args.extend(cols)

    return Table(*args)


def minimal_model_of(metadata: MetaData, clazz, to_keep: Set[str], exact_floats=False) -> Type[Model]:
    """
        Same as just above, but return a proper Model.
    """
    min_tbl = minimal_table_of(metadata, clazz, to_keep, exact_floats)

    class Ret(Model):
        __table__ = min_tbl

    return Ret


def any_(items_list: Union[List[int], List[str]]):
    # TODO: Get proper mapping, it seems a bit too much for sqlalchemy-stubs
    # noinspection PyTypeChecker
    return _pg_any(items_list)  # type: ignore


def all_(items_list: Union[List[int], List[str]]):
    # TODO: Get proper mapping, it seems a bit too much for sqlalchemy-stubs
    # noinspection PyTypeChecker
    return _pg_all(items_list)  # type: ignore


def only_res(res: List[Tuple[Any]]):
    """
        SQLAlchemy or DBApi returns even single column queries as lists of 1-element tuple :(
    """
    return [an_id for an_id, in res]
