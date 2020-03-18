# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Ye olde utils no project can do without :)
#
import math
import re

from astral import LocationInfo
from astral.sun import sun


def clean_value(value: str):
    """
    Remove spaces and map 2 special values to empty string, assuming the parameter is not None.
    :param value:
    :return:
    """
    value = value.strip()
    #    if len(value) < 4 and value.lower() in ('nan', 'na'):
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


def calc_astral_day_time(date, time, latitude, longitude):
    """
    Compute sun position for given coordinates and time.
    :param date: UTC date
    :param time: UTC time
    :param latitude: latitude
    :param longitude: longitude
    :return: D for Day, U for Dusk, N for Night, A pour Dawn (Aube in French)
    """
    l = LocationInfo()
    l.solar_depression = 'nautical'
    l.latitude = latitude
    l.longitude = longitude
    s = sun(l.observer, date=date)
    # print(Date,Time,Latitude,Longitude,s,)
    ret = '?'
    interp = ({'d': 'sunrise', 'f': 'sunset', 'r': 'D'}
              , {'d': 'sunset', 'f': 'dusk', 'r': 'U'}
              , {'d': 'dusk', 'f': 'dawn', 'r': 'N'}
              , {'d': 'dawn', 'f': 'sunrise', 'r': 'A'}
              )
    for i in interp:
        if s[i['d']].time() < s[i['f']].time() \
                and (time >= s[i['d']].time() and time <= s[i['f']].time()):
            ret = i['r']
        elif s[i['d']].time() > s[i['f']].time() \
                and (time >= s[i['d']].time() or time <= s[i['f']].time()):
            # Change of day b/w the 2 parts of the interval
            ret = i['r']
    return ret


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
    else:  # historical format, decimal part was in minutes
        v = to_float(v)
        f, i = math.modf(v)
        return i + (f / 0.6)
