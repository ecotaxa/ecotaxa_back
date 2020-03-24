# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Ye olde utils no project can do without :)
#
import datetime
import math
import re

from astral import LocationInfo, Depression
from astral.sun import sun
from pytz import utc


def clean_value(value: str):
    """
    Remove spaces and map 2 special values to empty string, assuming the parameter is not None.
    :param value:
    :return:
    """
    value = value.strip()
    #    if len(value) < 4 and value.lower() in ('nan', 'na'):
    # TODO: Use RE and benchmark
    if value.lower() in ('nan', 'na'):
        return ''
    return value


def clean_value_and_none(value: str):
    """
        Like previous but filter None as well
    """
    if value is None:
        return ''
    value = value.strip()
    #    if len(value) < 4 and value.lower() in ('nan', 'na'):
    if value.lower() in ('nan', 'na'):
        return ''
    return value


def to_float(value: str):
    """
    Convert input str to a python float.
    :param value:
    :return:
    """
    if value == '':
        return None
    try:
        return float(value)
    except ValueError:
        return None


def none_to_empty(value: str):
    """
    Map None to empty string or just return input value.
    :param value: None or any string
    :return:
    """
    if value is None:
        return ''
    return value


def calc_astral_day_time(date: datetime.datetime, time, latitude, longitude):
    """
    Compute sun position for given coordinates and time.
    :param date: UTC date
    :param time: UTC time
    :param latitude: latitude
    :param longitude: longitude
    :return: D for Day, U for Dusk, N for Night, A pour Dawn (Aube in French)
    """
    l = LocationInfo()
    l.latitude = latitude
    l.longitude = longitude
    s = sun(l.observer, date=date, dawn_dusk_depression=Depression.NAUTICAL)
    ret = '?'
    # The intervals and their interpretation
    interp = ({'from:': s['dusk'].time(), 'to:': s['dawn'].time(), '=>': 'N'},
              {'from:': s['dawn'].time(), 'to:': s['sunrise'].time(), '=>': 'A'},
              {'from:': s['sunrise'].time(), 'to:': s['sunset'].time(), '=>': 'D'},
              {'from:': s['sunset'].time(), 'to:': s['dusk'].time(), '=>': 'U'},
              )
    for intrv in interp:
        if (intrv['from:'] < intrv['to:']
                and intrv['from:'] <= time <= intrv['to:']):
            # Normal interval
            ret = intrv['=>']
        elif intrv['from:'] > intrv['to:'] \
                and (time >= intrv['from:'] or time <= intrv['to:']):
            # Change of day b/w the 2 parts of the interval
            ret = intrv['=>']

    return ret


ONE_DAY = datetime.timedelta(days=1)


def calc_astral_day_time2(date: datetime.datetime, time, latitude, longitude):
    """
    Compute sun position for given coordinates and time.
    :param date: UTC date
    :param time: UTC time
    :param latitude: latitude
    :param longitude: longitude
    :return: D for Day, U for Dusk, N for Night, A pour Dawn (Aube in French)
    """
    loc = LocationInfo()
    loc.latitude = latitude
    loc.longitude = longitude
    sun_phases = sun(observer=loc.observer, date=date, dawn_dusk_depression=Depression.NAUTICAL)
    observation_time = datetime.datetime.combine(date, time, tzinfo=utc)
    if observation_time < sun_phases['dawn']:
        sun_phases = sun(observer=loc.observer, date=date - ONE_DAY, dawn_dusk_depression=Depression.NAUTICAL)
    elif observation_time > sun_phases['dusk']:
        sun_phases = sun(observer=loc.observer, date=date + ONE_DAY, dawn_dusk_depression=Depression.NAUTICAL)
    # The intervals and their interpretation
    interp = [
        {'from:': sun_phases['dawn'], 'to:': sun_phases['sunrise'], '=>': 'A'},
        {'from:': sun_phases['sunrise'], 'to:': sun_phases['sunset'], '=>': 'D'},
        {'from:': sun_phases['sunset'], 'to:': sun_phases['dusk'], '=>': 'U'},
    ]
    for intrv in interp:
        if intrv['from:'] <= observation_time <= intrv['to:']:
            return intrv['=>']
    return '?'


def encode_equal_list(map: dict):
    """
        Turn a dict into a string key=value, with sorted keys.
    :param map:
    :return:
    """
    l = ["%s=%s" % (k, v) for k, v in map.items()]
    l.sort()
    return "\n".join(l)


def decode_equal_list(txt):
    """
        Inverse of previous
    :param map:
    :return:
    """
    res = {}
    for l in str(txt).splitlines():
        ls = l.split('=', 1)
        if len(ls) == 2:
            res[ls[0].strip().lower()] = ls[1].strip().lower()
    return res


# TODO: Most probably better elsewhere
def convert_degree_minute_float_to_decimal_degree(v):
    m = re.search(r"(-?\d+)°(\d+) (\d+)", v)
    if m:  # data in format DDD°MM SSS
        parts = [float(x) for x in m.group(1, 2, 3)]
        parts[1] += parts[2] / 60  # on ajoute les secondes en fraction des minutes
        parts[0] += parts[1] / 60  # on ajoute les minutes en fraction des degrés
        return parts[0]
    else:  # decimal part was in minutes
        # Bug in 2.2 @see https://github.com/oceanomics/ecotaxa_dev/issues/340
        v = to_float(v)
        f, i = math.modf(v)
        return i + (f / 0.6)
