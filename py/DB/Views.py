# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# OK the file is named 'views' and we have a single one...
# Anyway this view is for easier direct SQL query and should not be used in present app.
#
from typing import List

from sqlalchemy import Table, text
from sqlalchemy_views import CreateView, DropView  # type:ignore # case6

OBJECTS_DEF = text(
    """select sam.projid, sam.sampleid, obh.objid, obh.latitude, obh.longitude,
              obh.objdate, obh.objtime, obh.depth_min, obh.depth_max,
              obh.classif_id, obh.classif_qual, obh.classif_who, 
              CASE WHEN obh.classif_qual in ('V', 'D') THEN obh.classif_date END AS classif_when,
              obh.classif_score AS classif_auto_score,
              CASE WHEN obh.classif_qual = 'P' THEN obh.classif_date END AS classif_auto_when,
              CASE WHEN obh.classif_qual = 'P' THEN obh.classif_id END AS classif_auto_id,
              NULL::integer AS classif_crossvalidation_id,
              obh.complement_info,
              NULL::double precision AS similarity,
              obh.sunpos,
              HASHTEXT(obh.orig_id) AS random_value,
              obh.acquisid, obh.object_link, obh.orig_id, obh.acquisid AS processid, 
              ofi.*
         from obj_head obh
         join acquisitions acq on obh.acquisid = acq.acquisid
         join samples sam on acq.acq_sample_id = sam.sampleid 
         left join obj_field ofi on obh.objid = ofi.objfid -- allow elimination by planner
                    """
)


def views_deletion_queries(metadata) -> List:
    objects = Table("objects", metadata)

    drop_view = DropView(objects, if_exists=True)

    return [drop_view]


def views_creation_queries(metadata) -> List:
    objects = Table("objects", metadata)

    create_view = CreateView(objects, OBJECTS_DEF)

    return [create_view]
