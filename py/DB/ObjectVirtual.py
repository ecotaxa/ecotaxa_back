# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2024  Picheral, Colin, Irisson (UPMC-CNRS)
#
# The virtual columns for Object
from . import ObjectHeader
from .Object import PREDICTED_CLASSIF_QUAL, VALIDATED_CLASSIF_QUAL, DUBIOUS_CLASSIF_QUAL
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


class ClassifWhenVirtualColumn(VirtualColumn):
    name = "classif_when"
    sql = "CASE WHEN obh.classif_qual in ('V','D') THEN obh.classif_date END"

    @staticmethod
    def filler(header: ObjectHeader):
        return (
            header.classif_date
            if header.classif_qual in (VALIDATED_CLASSIF_QUAL, DUBIOUS_CLASSIF_QUAL)
            else None
        )


class ClassifAutoScoreVirtualColumn(VirtualColumn):
    name = "classif_auto_score"
    sql = "obh.classif_score"

    @staticmethod
    def filler(header: ObjectHeader):
        return header.classif_score


class ClassifAutoWhenVirtualColumn(VirtualColumn):
    name = "classif_auto_when"
    sql = "CASE WHEN obh.classif_qual='P' THEN obh.classif_date END"

    @staticmethod
    def filler(header: ObjectHeader):
        return (
            header.classif_date
            if header.classif_qual == PREDICTED_CLASSIF_QUAL
            else None
        )


class ClassifAutoIDVirtualColumn(VirtualColumn):
    name = "classif_auto_id"
    sql = "CASE WHEN obh.classif_qual='P' THEN obh.classif_id END"

    @staticmethod
    def filler(header: ObjectHeader):
        return (
            header.classif_id if header.classif_qual == PREDICTED_CLASSIF_QUAL else None
        )


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
    # ComplementInfoVirtualColumn,
    ImageCountVirtualColumn,
    RandomValueVirtualColumn,
    ClassifWhenVirtualColumn,
    ClassifAutoWhenVirtualColumn,
    ClassifAutoScoreVirtualColumn,
    ClassifAutoIDVirtualColumn,
    ClassifCrossValidationIDVirtualColumn,
    SimilarityVirtualColumn,
)
