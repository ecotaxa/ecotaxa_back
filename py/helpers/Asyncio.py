# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Helpers based on asyncio
#
import asyncio
from typing import Coroutine


def async_bg_run(coro: Coroutine):
    """
        Run in 'background' the given coroutine.
    """
    # Only starting 3.7 the def is officially exposed
    loop = asyncio.events._get_running_loop()
    return loop.create_task(coro)


async def async_sleep(tim: float):
    """
        Pseudo-sleep which gives control to other coroutines.
    """
    await asyncio.sleep(tim)


async def log_streamer(file_name: str, magic: str):
    """
        Return a file line by line, until the magic sentence is found.
    """
    while True:
        try:
            strm = open(file_name, "r")
            break
        except FileNotFoundError:
            await async_sleep(0.1)
    while True:
        ret = strm.readline()
        while len(ret) == 0:
            await async_sleep(0.5)
            pos = strm.tell()
            try:
                strm = open(file_name, "r")
                strm.seek(pos)
                ret = strm.readline()
            except IOError:  # pragma:nocover
                yield "IOERROR"
                break
        yield ret
        if magic in ret:
            break
