#
# TUS upload: the background unpack must survive the "looks sync" wait.
# After the wait times out, the unpack goes on, is still tracked, and its end is logged.
#
import asyncio
import gc
import logging
import time
from pathlib import Path

import pytest

import API_operations.BigFiles as BigFiles


class FakeUserDir:
    """Stands for UserFilesDirectory, with a slow unpack"""

    def __init__(self, duration: float, fail: bool = False):
        self.duration = duration
        self.fail = fail
        self.done = False

    def switch_to_background(self):
        pass

    def dispatch_unpack(self, compressed_path: Path, to_path: Path) -> None:
        time.sleep(self.duration)
        if self.fail:
            raise OSError("No space left on device")
        self.done = True


@pytest.fixture
def short_wait(monkeypatch):
    monkeypatch.setattr(BigFiles, "UNPACK_SYNC_WAIT", 0.1)


@pytest.fixture
def bigfiles_logs(monkeypatch):
    """Capture BigFiles log messages, whatever the app's logging setup"""
    messages = []

    class Capture(logging.Handler):
        def emit(self, record):
            messages.append(record.getMessage())

    handler = Capture(level=logging.DEBUG)
    BigFiles.logger.addHandler(handler)
    monkeypatch.setattr(BigFiles.logger, "disabled", False)
    old_level = BigFiles.logger.level
    BigFiles.logger.setLevel(logging.DEBUG)
    yield messages
    BigFiles.logger.setLevel(old_level)
    BigFiles.logger.removeHandler(handler)


async def _start(user_dir):
    p = Path("/nonexistent")
    return await BigFiles._start_unpack(user_dir, p, p / "a.zip", p, "a.zip")


def test_fast_unpack_waited(short_wait, bigfiles_logs):
    user_dir = FakeUserDir(0.01)

    async def scenario():
        task = await _start(user_dir)
        assert task.done() and not task.cancelled()

    asyncio.run(scenario())
    assert user_dir.done
    assert any("unpack done" in m for m in bigfiles_logs)


def test_slow_unpack_not_cancelled(short_wait, bigfiles_logs):
    user_dir = FakeUserDir(0.5)

    async def scenario():
        task = await _start(user_dir)
        # The wait timed out, but the unpack goes on, and is still tracked
        assert any("CONTINUES" in m for m in bigfiles_logs)
        assert not task.cancelled()
        assert task in BigFiles.background_tasks
        await task
        await asyncio.sleep(0)  # let done-callbacks run
        assert task not in BigFiles.background_tasks

    asyncio.run(scenario())
    assert user_dir.done
    assert any("Done unpacking" in m for m in bigfiles_logs)


def test_slow_unpack_failure_logged(short_wait, bigfiles_logs):
    user_dir = FakeUserDir(0.3, fail=True)
    unretrieved = []

    async def scenario():
        asyncio.get_running_loop().set_exception_handler(
            lambda loop, ctx: unretrieved.append(ctx.get("message"))
        )
        await _start(user_dir)
        # Nobody awaits the task anymore, like in the TUS hook
        while BigFiles.background_tasks:
            await asyncio.sleep(0.05)
        gc.collect()

    asyncio.run(scenario())
    gc.collect()
    assert any("Error unpacking" in m for m in bigfiles_logs)
    assert unretrieved == []
