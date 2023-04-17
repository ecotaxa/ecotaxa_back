# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
from datetime import time, date
from typing import Optional

from astral import LocationInfo, Depression  # type: ignore
from astral.sun import sun  # type: ignore
from typing_extensions import TypedDict

# TODO: Caching a single value is useful, but less than several of them
from DB.helpers.Bean import Bean


class AstralCache(TypedDict, total=False):
    date: date
    time: Optional[time]
    long: Optional[float]
    lat: Optional[float]
    r: Optional[str]


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
    interp = (
        {"from:": s["dusk"].time(), "to:": s["dawn"].time(), "=>": "N"},
        {"from:": s["dawn"].time(), "to:": s["sunrise"].time(), "=>": "A"},
        {"from:": s["sunrise"].time(), "to:": s["sunset"].time(), "=>": "D"},
        {"from:": s["sunset"].time(), "to:": s["dusk"].time(), "=>": "U"},
    )
    for intrv in interp:
        if intrv["from:"] < intrv["to:"] and intrv["from:"] <= time <= intrv["to:"]:
            # Normal interval
            ret = intrv["=>"]
        elif intrv["from:"] > intrv["to:"] and (
                time >= intrv["from:"] or time <= intrv["to:"]
        ):
            # Change of day b/w the 2 parts of the interval
            ret = intrv["=>"]

    return ret
