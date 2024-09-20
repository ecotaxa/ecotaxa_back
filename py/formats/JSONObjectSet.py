# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Description on how to move from DB rows to JSON-compatible dicts
#
from typing import Dict, Union, Callable

from DB.Acquisition import Acquisition
from DB.Image import Image
from DB.Object import ObjectHeader, ObjectFields
from DB.Process import Process
from DB.Project import Project
from DB.Sample import Sample
from DB.helpers.ORM import ModelT, Column, RelationshipProperty

# Typing for the clarity. Key = DB Column, Value = string in target dict
JSONDesc = Dict[Union[Column, RelationshipProperty, Callable], str]

JSON_FIELDS: Dict[ModelT, JSONDesc] = {
    Project: {
        Project.title: "ttl",
        Project.all_samples: "samples",  # type:ignore # case2
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
        ObjectHeader.classif_when: "cwhn",
        ObjectHeader.classif_who: "mwho",
        # ObjectHeader.classif_auto_id: "acat",
        ObjectHeader.all_images: "images",  # type:ignore # case2
        ObjectHeader.depth_min: "depth_min",
        ObjectHeader.depth_max: "depth_max",
        ObjectHeader.latitude: "latitude",
        ObjectHeader.longitude: "longitude",
        ObjectHeader.complement_info: "cmt",
        ObjectHeader.fields: "fields",  # type:ignore # 1-1 so should be joined right away and disappear
    },
    ObjectFields: {},
    Image: {Image.img_to_file: "fil", Image.imgrank: "rnk"},
}
