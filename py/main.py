# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

PredefinedFields = {
    # A mapping from TSV columns to objects and fields
    'object_id': {'table': 'obj_field', 'field': 'orig_id', 'type': 't'},
    'sample_id': {'table': 'sample', 'field': 'orig_id', 'type': 't'},
    'acq_id': {'table': 'acq', 'field': 'orig_id', 'type': 't'},
    'process_id': {'table': 'process', 'field': 'orig_id', 'type': 't'},
    'object_lat': {'table': 'obj_head', 'field': 'latitude', 'type': 'n'},
    'object_lon': {'table': 'obj_head', 'field': 'longitude', 'type': 'n'},
    'object_date': {'table': 'obj_head', 'field': 'objdate', 'type': 't'},
    'object_time': {'table': 'obj_head', 'field': 'objtime', 'type': 't'},
    'object_link': {'table': 'obj_field', 'field': 'object_link', 'type': 't'},
    'object_depth_min': {'table': 'obj_head', 'field': 'depth_min', 'type': 'n'},
    'object_depth_max': {'table': 'obj_head', 'field': 'depth_max', 'type': 'n'},
    'object_annotation_category': {'table': 'obj_head', 'field': 'classif_id', 'type': 't'},
    'object_annotation_category_id': {'table': 'obj_head', 'field': 'classif_id', 'type': 'n'},
    # TODO: Does it work in Prod DB????
    # 'object_annotation_time': {'table': 'obj_head', 'field': 'tmp_annottime', 'type': 't'},
    # 'object_annotation_person_email': {'table': 'obj_head', 'field': 'tmp_annotemail', 'type': 't'},
    # 'annotation_person_first_name': {'table': 'obj_head', 'field': 'tmp_todelete1', 'type': 't'},
    # end TODO
    'object_annotation_date': {'table': 'obj_head', 'field': 'classif_when', 'type': 't'},
    'object_annotation_person_name': {'table': 'obj_head', 'field': 'classif_who', 'type': 't'},
    'object_annotation_status': {'table': 'obj_head', 'field': 'classif_qual', 'type': 't'},
    'img_rank': {'table': 'image', 'field': 'imgrank', 'type': 'n'},
    'img_file_name': {'table': 'image', 'field': 'orig_file_name', 'type': 't'},
    'sample_dataportal_descriptor': {'table': 'sample', 'field': 'dataportal_descriptor', 'type': 't'},
    'acq_instrument': {'table': 'acq', 'field': 'instrument', 'type': 't'},
}

if __name__ == '__main__':
    # TODO: Start server here or parse args for single call
    pass
