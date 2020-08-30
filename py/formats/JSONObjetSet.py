# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Description on how to move from DB rows to JSON-compatible dicts
#
from typing import Dict, Union

from sqlalchemy.orm import RelationshipProperty

from DB import Project, Sample, Acquisition, Process, ObjectHeader, ObjectFields, Image
from DB.helpers.ORM import ModelT, Column

# Typing for the clarity. Key = DB Column, Value = string in target dict
JSONDesc = Dict[Union[Column, RelationshipProperty], str]

JSON_FIELDS: Dict[ModelT, JSONDesc] = {
    Project: {Project.title: "ttl",
              Project.all_samples: "samples"},
    Sample: {Sample.sampleid: "id",
             Sample.orig_id: "sid",
             Sample.dataportal_descriptor: "dsc",
             Sample.all_acquisitions: "acquisitions"
             },
    Acquisition: {Acquisition.acquisid: "id",
                  Acquisition.orig_id: "aid",
                  Acquisition.all_processes: "processings"
                  },
    Process: {Process.processid: "id",
              Process.orig_id: "pid",
              Process.all_objects: "objects"
              },
    ObjectHeader: {ObjectHeader.classif_id: "mcat",
                   ObjectHeader.classif_auto_id: "acat",
                   ObjectHeader.all_images: "images",
                   ObjectHeader.fields: "fields"  # 1-1 so should be joined right away and disappear
                   },
    ObjectFields: {ObjectFields.orig_id: "oid"
                   },
    Image: {Image.file_name: "fil",
            Image.imgrank: "rnk"
            }
}
