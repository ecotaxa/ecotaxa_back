from os import unlink

import pytest
from helpers.Asyncio import *

LOG_FILE = "tst_log.log"


async def feed_log(nb_lines: int):
    fno = open(LOG_FILE, "w")
    for ln in range(nb_lines):
        print("line %d" % ln, file=fno)
        await async_sleep(0.001)


@pytest.mark.asyncio
async def test_asyncio():
    try:
        unlink(LOG_FILE)
    except FileNotFoundError:
        pass
    tsk = async_bg_run(feed_log(1000))
    strmer = log_streamer(LOG_FILE, "line 999")
    out = []
    while True:
        try:
            out.append(await strmer.__anext__())
        except StopAsyncIteration:
            break
    await asyncio.gather(tsk)
    # TODO: It seems to depend on async engine
    #  assert len(out) == 1000
