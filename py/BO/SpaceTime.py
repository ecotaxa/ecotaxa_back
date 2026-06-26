# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
from datetime import time, date
from typing import Optional, TypedDict

from astral import LocationInfo, Depression
from astral.sun import sun

# TODO: Caching a single value is useful, but less than several of them
from DB.helpers.Bean import Bean


class AstralCache(TypedDict, total=False):
    date: date
    time: Optional[time]
    long: Optional[float]
    lat: Optional[float]
    r: Optional[str]


class SunInterval(TypedDict):
    from_time: time
    to_time: time
    interpretation: str


astral_cache: AstralCache = {
    "date": date(1, 1, 1),
    "time": None,
    "long": None,
    "lat": None,
    "r": "?",
}

USED_FIELDS_FOR_SUNPOS = {"objdate", "objtime", "longitude", "latitude"}


def compute_sun_position(object_head_to_write: Bean):
    # Compute sun position if not already done
    global astral_cache
    if not (
        astral_cache["date"] == object_head_to_write.objdate
        and astral_cache["time"] == object_head_to_write.objtime
        and astral_cache["long"] == object_head_to_write.longitude
        and astral_cache["lat"] == object_head_to_write.latitude
    ):
        # Columns in definition are indeed nullable
        if (
            object_head_to_write.objdate is None
            or object_head_to_write.objtime is None
            or object_head_to_write.longitude is None
            or object_head_to_write.latitude is None
        ):
            return "?"
        astral_cache = {
            "date": object_head_to_write.objdate,
            "time": object_head_to_write.objtime,
            "long": object_head_to_write.longitude,
            "lat": object_head_to_write.latitude,
            "r": "",
        }
        astral_cache["r"] = calc_astral_day_time(
            astral_cache["date"],
            astral_cache["time"],
            astral_cache["lat"],
            astral_cache["long"],
        )
    return astral_cache["r"]


def calc_astral_day_time(date: datetime.date, time, latitude, longitude):
    """
    Compute sun position for given coordinates and time.
    :param date: UTC date
    :param time: UTC time
    :param latitude: latitude
    :param longitude: longitude
    :return: D for Day, U for Dusk, N for Night, A for Dawn (Aube in French)
    """
    loc = LocationInfo()
    loc.latitude = latitude
    loc.longitude = longitude
    s = sun(loc.observer, date=date, dawn_dusk_depression=Depression.NAUTICAL)
    ret = "?"
    # The intervals and their interpretation
    interp: tuple[SunInterval, ...] = (
        {
            "from_time": s["dusk"].time(),
            "to_time": s["dawn"].time(),
            "interpretation": "N",
        },
        {
            "from_time": s["dawn"].time(),
            "to_time": s["sunrise"].time(),
            "interpretation": "A",
        },
        {
            "from_time": s["sunrise"].time(),
            "to_time": s["sunset"].time(),
            "interpretation": "D",
        },
        {
            "from_time": s["sunset"].time(),
            "to_time": s["dusk"].time(),
            "interpretation": "U",
        },
    )
    for intrv in interp:
        if (
            intrv["from_time"] < intrv["to_time"]
            and intrv["from_time"] <= time <= intrv["to_time"]
        ):
            # Normal interval
            ret = intrv["interpretation"]
        elif intrv["from_time"] > intrv["to_time"] and (
            time >= intrv["from_time"] or time <= intrv["to_time"]
        ):
            # Change of day b/w the 2 parts of the interval
            ret = intrv["interpretation"]

    return ret
