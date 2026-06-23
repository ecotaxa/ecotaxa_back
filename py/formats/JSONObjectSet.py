# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Description on how to move from DB rows to JSON-compatible dicts
#
from typing import Dict, Union, Callable, Any, List

from sqlalchemy.orm import InstrumentedAttribute, Mapped

from DB.Acquisition import Acquisition
from DB.Image import Image
from DB.Object import ObjectHeader, ObjectFields
from DB.Process import Process
from DB.Project import Project
from DB.Sample import Sample
from DB.helpers.ORM import ModelT, Model

# Typing for the clarity. Key = DB Column, Value = string in target dict
JSONDesc = Dict[
    Union[Model, List[Any], InstrumentedAttribute[Any], Mapped[Any], Callable], str
]

JSON_FIELDS: Dict[ModelT, JSONDesc] = {
    Project: {
        Project.title: "ttl",
        Project.all_samples: "samples",
    },
    Sample: {
        Sample.sampleid: "id",
        Sample.orig_id: "sid",
        Sample.dataportal_descriptor: "dsc",
        Sample.all_acquisitions: "acquisitions",
    },
    Acquisition: {
        Acquisition.acquisid: "id",
        Acquisition.orig_id: "aid",
        Acquisition.process: "processings",
        Acquisition.all_objects: "objects",
    },
    Process: {
        Process.processid: "id",
        Process.orig_id: "pid",
    },
    ObjectHeader: {
        ObjectHeader.orig_id: "oid",
        ObjectHeader.classif_id: "ccat",
        ObjectHeader.classif_date: "cdte",
        ObjectHeader.classif_who: "mwho",
        ObjectHeader.all_images: "images",
        ObjectHeader.depth_min: "depth_min",
        ObjectHeader.depth_max: "depth_max",
        ObjectHeader.latitude: "latitude",
        ObjectHeader.longitude: "longitude",
        ObjectHeader.complement_info: "cmt",
        ObjectHeader.fields: "fields",  # 1-1 so should be joined right away and disappear
    },
    ObjectFields: {},
    Image: {Image.img_to_file: "fil", Image.imgrank: "rnk"},
}
