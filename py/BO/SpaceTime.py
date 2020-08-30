# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from datetime import time, date
from typing import Optional
from typing_extensions import TypedDict

from BO.helpers.TSVHelpers import calc_astral_day_time
from DB.Object import ObjectHeader


# TODO: Caching a single value is useful, but less than several of them
# TODO: a TypedDict is more accurate for typing
class AstralCache(TypedDict, total=False):
    date: date
    time: Optional[time]
    long: Optional[float]
    lat: Optional[float]
    r: Optional[str]


astral_cache: AstralCache = {'date': date(1, 1, 1), 'time': None, 'long': None, 'lat': None, 'r': '?'}

USED_FIELDS_FOR_SUNPOS = {'objdate', 'objtime', 'longitude', 'latitude'}


def compute_sun_position(object_head_to_write: ObjectHeader):
    # Compute sun position if not already done
    global astral_cache
    if not (astral_cache['date'] == object_head_to_write.objdate
            and astral_cache['time'] == object_head_to_write.objtime
            and astral_cache['long'] == object_head_to_write.longitude
            and astral_cache['lat'] == object_head_to_write.latitude):
        # Columns in definition are indeed nullable
        if (object_head_to_write.objdate is None or
                object_head_to_write.objtime is None or
                object_head_to_write.longitude is None or
                object_head_to_write.latitude is None):
            return '?'
        astral_cache = {'date': object_head_to_write.objdate,
                        'time': object_head_to_write.objtime,
                        'long': object_head_to_write.longitude,
                        'lat': object_head_to_write.latitude,
                        'r': ''}
        astral_cache['r'] = calc_astral_day_time(astral_cache['date'],
                                                 astral_cache['time'],
                                                 astral_cache['lat'],
                                                 astral_cache['long'])
    return astral_cache['r']
