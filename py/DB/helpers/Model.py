# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

# noinspection PyUnreachableCode
if False:  # pragma: no cover
    from sqlalchemy import Column, Table, MetaData
    from sqlalchemy.inspection import inspect
    from typing import Set, List, Union, Type

    from DB.helpers.ORM import Model

    def view_of(_metadata, clazz, to_keep: Set[str]) -> Type[Model]:
        """
            Return a Model, i.e. a SQLAlchemy mapper with only the given fields.
        :param _metadata: unused
        :param clazz: the base mapper class
        :param to_keep: the column (fields) names to keep
        :return: new class
        """
        # Create the ORM view with PK + mandatory fields + wanted fields
        insp = inspect(clazz)
        incl = []
        for a_col in insp.columns:
            if a_col.primary_key or not a_col.nullable or a_col.name in to_keep:
                incl.append(a_col.name)

        class Ret(Model):
            __tablename__ = clazz.__tablename__
            __mapper_args__ = {"include_properties": incl}

        return Ret

    def partial_clone_of(
        metadata: MetaData, clazz, to_keep: Set[str], new_pks: List[Union[str, tuple]]
    ) -> Type[Model]:
        """
            Return a Model, i.e. a SQLAlchemy mapper Class with only the given fields.
        :param new_pks: The new primary keys to add to produced mapper.
        :param metadata: SQLAlchemy metadata repository.
        :param clazz: the base mapper class
        :param to_keep: the column (fields) names to keep
        :return: new class
        """
        # Create the ORM clone with PK + mandatory fields + wanted fields
        insp = inspect(clazz)
        cols = []
        a_col: Column
        for a_col in insp.columns:
            if a_col.primary_key:
                # Make PK an ordinary column
                cols.append(Column(name=a_col.name, type_=a_col.type))
            elif not a_col.nullable or a_col.name in to_keep:
                clone_col = a_col.copy()
                cols.append(clone_col)
                if a_col.name in new_pks:
                    clone_col.primary_key = True
        # Add extra PK column
        for a_pk in new_pks:
            if isinstance(a_pk, tuple):
                (name, type_) = a_pk
                cols.append(Column(name=name, type_=type_, primary_key=True))
        args = ["temp_" + clazz.__tablename__, metadata]
        args.extend(cols)

        ret = Table(*args, prefixes=["TEMPORARY"])

        # Create class on the fly
        class Ret(Model):
            __table__ = ret

        return Ret


# if __name__ == '__main__':
#     def print_table(tbl: Table):
#         print(CreateTable(tbl).compile(dialect=postgresql.dialect()))
