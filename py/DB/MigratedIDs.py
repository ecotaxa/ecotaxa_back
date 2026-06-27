# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)

from sqlalchemy import Index
from sqlalchemy.orm import mapped_column

from .helpers.ORM import Model, Mapped
from .helpers.Postgres import BIGINT, INTEGER


class ObjidOld2New(Model):
    __tablename__ = "objid_old_2_new"
    old_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False, nullable=True)
    new_id: Mapped[int] = mapped_column(BIGINT)


Index(
    "objid_mapping_old_to_new",
    ObjidOld2New.old_id,
    postgresql_include=[ObjidOld2New.new_id],
    unique=True,
)
Index(
    "objid_mapping_new_to_old",
    ObjidOld2New.new_id,
    postgresql_include=[ObjidOld2New.old_id],
    unique=True,
)


class SampleIdOld2New(Model):
    __tablename__ = "samid_old_2_new"
    old_id: Mapped[int] = mapped_column(INTEGER, primary_key=True, autoincrement=False, nullable=True)
    new_id: Mapped[int] = mapped_column(BIGINT)


class AcquisIdOld2New(Model):
    __tablename__ = "acqid_old_2_new"
    old_id: Mapped[int] = mapped_column(INTEGER, primary_key=True, autoincrement=False, nullable=True)
    new_id: Mapped[int] = mapped_column(BIGINT)


Index(
    "acquisid_mapping_idx",
    AcquisIdOld2New.new_id,
    postgresql_include=[AcquisIdOld2New.old_id],
)
Index(
    "acquisid_mapping_idx2",
    AcquisIdOld2New.old_id,
    postgresql_include=[AcquisIdOld2New.new_id],
)
