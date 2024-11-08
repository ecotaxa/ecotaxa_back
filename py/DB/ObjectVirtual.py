# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2024  Picheral, Colin, Irisson (UPMC-CNRS)
#
# The virtual columns for Object
from . import ObjectHeader
from .helpers.VirtualColumn import VirtualColumnSet, VirtualColumn


class ComplementInfoVirtualColumn(
    VirtualColumn
):  # Note: unused so far as the DB column is still present
    name = "complement_info"
    sql = "NULL::text"

    @staticmethod
    def filler(_header: ObjectHeader):
        return None


class ImageCountVirtualColumn(VirtualColumn):
    name = "imgcount"
    sql = "(SELECT COUNT(img2.imgrank) FROM images img2 WHERE img2.objid = obh.objid)"

    @staticmethod
    def filler(header: ObjectHeader):
        return len(header.all_images)


class RandomValueVirtualColumn(VirtualColumn):
    name = "random_value"
    sql = "HASHTEXT(obh.orig_id)"

    @staticmethod
    def filler(header: ObjectHeader):
        return hash(header.orig_id)


class ClassifCrossValidationIDVirtualColumn(VirtualColumn):
    name = "classif_crossvalidation_id"
    sql = "NULL::integer"

    @staticmethod
    def filler(_header: ObjectHeader):
        return None


class SimilarityVirtualColumn(VirtualColumn):
    name = "similarity"
    sql = "NULL::float"

    @staticmethod
    def filler(_header: ObjectHeader):
        return None


OBJECT_VIRTUAL_COLUMNS: VirtualColumnSet = VirtualColumnSet(
    ComplementInfoVirtualColumn,
    ImageCountVirtualColumn,
    RandomValueVirtualColumn,
    ClassifCrossValidationIDVirtualColumn,
    SimilarityVirtualColumn,
)
