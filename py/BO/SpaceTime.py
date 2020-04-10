# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

from db.Object import Object
from utils import calc_astral_day_time

# TODO: Caching a single value is useful, but less than several of them
astral_cache = {'date': None, 'time': None, 'long': None, 'lat': None, 'r': ''}


def compute_sun_position(object_head_to_write: Object):
    # Compute sun position if not already done
    global astral_cache
    if not (astral_cache['date'] == object_head_to_write.objdate
            and astral_cache['time'] == object_head_to_write.objtime
            and astral_cache['long'] == object_head_to_write.longitude
            and astral_cache['lat'] == object_head_to_write.latitude):
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
