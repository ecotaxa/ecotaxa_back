# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import Optional, Iterable, Tuple, List, Set, Dict, TypeVar, Type

# noinspection PyUnresolvedReferences
from sqlalchemy import Column, inspect, MetaData, Table, any_ as _pg_any, and_
# noinspection PyUnresolvedReferences
from sqlalchemy.dialects import postgresql
# noinspection PyUnresolvedReferences
from sqlalchemy.engine.result import ResultProxy
from sqlalchemy.ext.declarative import declarative_base
# noinspection PyUnresolvedReferences
from sqlalchemy.orm import Session, Query, make_transient, contains_eager
# For exporting
# noinspection PyUnresolvedReferences
from sqlalchemy.orm import relationship
# noinspection PyUnresolvedReferences
from sqlalchemy.sql import Insert, Update, Delete

_Base = declarative_base()


class Model(_Base):
    __abstract__ = True  # prevent SQLAlchemy from trying to map
    __tablename__: str


# Just forD fun :)
ModelT = Type[Model]

# Generics on some ORM operations
M = TypeVar('M', bound=Model)


def orm_equals(an_obj: Model, another_obj: Model) -> bool:
    """
        Compare values of 2 ORM objects, excluding PK and FK.
    """
    to_copy, to_clear = _analyze_cols(an_obj.__table__)
    for a_col in to_copy:
        if getattr(an_obj, a_col) != getattr(another_obj, a_col):
            return False
    return True


def clone_of(an_obj: Optional[M]) -> Optional[M]:
    """
        Return a clone (same class, same plain values) of the ORM-mapped object.
        Keys are not copied, for safety.
        None in, None out.
        :param an_obj:
        :return:
    """
    if an_obj is None:
        return None
    table = an_obj.__table__
    ret = an_obj.__class__()
    a_col: Column
    for a_col in table.columns:
        col_name = a_col.name
        if a_col.primary_key or a_col.foreign_keys:
            pass
        else:
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


def detach_all_from_session(session: Session, an_orm_collection: Iterable[Model]) -> None:
    """
        Detach from the session all object in the given Container.
        :param session:
        :param an_orm_collection: An iterable of SQLAlchemy produced instance.
        :return:
    """
    for an_orm in an_orm_collection:
        detach_from_session(session, an_orm)


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
    a_col: Column
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


def minimal_table_of(metadata: MetaData, clazz, to_keep: Set[str]) -> Table:
    """
        Return a Table, i.e. a SQLAlchemy mapper, with only the given fields.
    :param metadata: SQLAlchemy metadata repository.
    :param clazz: the base mapper class
    :param to_keep: the column (fields) names to keep
    :return: new Table
    """
    # Create the ORM clone with PK + mandatory fields + wanted fields
    insp = inspect(clazz)
    cols = []
    a_col: Column
    for a_col in insp.columns:
        if a_col.primary_key or not a_col.nullable or a_col.name in to_keep:
            clone_col = a_col.copy()
            cols.append(clone_col)
    args = [clazz.__tablename__, metadata]
    args.extend(cols)

    return Table(*args)


def any_(int_list: List[int]):
    # TODO: Get proper mapping, it seems a bit too much for sqlalchemy-stubs
    return _pg_any(int_list)  # type: ignore
