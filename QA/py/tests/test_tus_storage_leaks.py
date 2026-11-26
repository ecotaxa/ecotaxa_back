# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
import asyncio
import threading
from pathlib import Path

import pytest
from starlette import status
from tuspyserver.lock import acquire_upload_lock

from tests.credentials import CREATOR_AUTH

TUS_UPLOAD_URL = "/user_files/upload/"
TUS_VERSION = "1.0.0"


def test_split_storage_append_bounded_by_threshold(tmp_path):
    """append() flushes automatically once buffered bytes reach MAX_PENDING_BYTES."""
    from API_operations.BigFiles import SplitLocalFileStorage

    storage = SplitLocalFileStorage(
        files_dir=str(tmp_path / "files"),
        info_dir=str(tmp_path / "info"),
    )
    storage.MAX_PENDING_BYTES = 1024

    async def scenario():
        uid = "a" * 32
        await storage.create(uid)
        async with storage.lock(uid):
            await storage.append(uid, b"x" * 600)
            assert len(storage._pending[uid]) == 600
            await storage.append(uid, b"y" * 600)
            # Threshold reached -> flushed to disk, _pending cleared
            assert uid not in storage._pending
            assert await storage.size(uid) == 1200

    asyncio.run(scenario())


def test_split_storage_pending_cleared_on_error_and_cancel(tmp_path):
    """_pending[uid] is always freed when lock() exits via exception or cancellation."""
    from API_operations.BigFiles import SplitLocalFileStorage

    storage = SplitLocalFileStorage(
        files_dir=str(tmp_path / "files"),
        info_dir=str(tmp_path / "info"),
    )

    async def scenario():
        uid1 = "b" * 32
        await storage.create(uid1)
        with pytest.raises(RuntimeError):
            async with storage.lock(uid1):
                await storage.append(uid1, b"partial-data")
                assert uid1 in storage._pending
                raise RuntimeError("boom mid-stream")
        assert uid1 not in storage._pending

        uid2 = "c" * 32
        await storage.create(uid2)

        async def cancelled_patch():
            async with storage.lock(uid2):
                await storage.append(uid2, b"partial-cancel")
                await asyncio.sleep(10)

        task = asyncio.create_task(cancelled_patch())
        await asyncio.sleep(0.05)
        assert uid2 in storage._pending
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert uid2 not in storage._pending

    asyncio.run(scenario())


def test_tus_patch_exceeding_length_does_not_leak_pending(fastapi):
    """HTTPException mid-stream in tuspyserver must not leave _pending[uuid] in hybrid_storage."""
    from API_operations.BigFiles import hybrid_storage

    res_post = fastapi.post(
        TUS_UPLOAD_URL,
        headers={
            "Tus-Resumable": TUS_VERSION,
            "Upload-Length": "10",
            **CREATOR_AUTH,
        },
    )
    assert res_post.status_code == status.HTTP_201_CREATED
    upload_url = res_post.headers["Location"]
    uid = upload_url.rstrip("/").split("/")[-1]

    try:
        res_patch = fastapi.patch(
            upload_url,
            headers={
                "Tus-Resumable": TUS_VERSION,
                "Content-Type": "application/offset+octet-stream",
                "Upload-Offset": "0",
                **CREATOR_AUTH,
            },
            content=b"0123456789ABCDEF",  # 16 bytes > Upload-Length 10
        )
        assert res_patch.status_code == status.HTTP_400_BAD_REQUEST
        assert uid not in hybrid_storage._pending
    finally:
        fastapi.delete(
            upload_url,
            headers={"Tus-Resumable": TUS_VERSION, **CREATOR_AUTH},
        )


def test_split_storage_lock_no_fd_leak_on_cancel_while_waiting(tmp_path):
    """Cancelling while waiting on lock() must still release the underlying FileLock once acquired."""
    from API_operations.BigFiles import SplitLocalFileStorage

    storage = SplitLocalFileStorage(
        files_dir=str(tmp_path / "files"),
        info_dir=str(tmp_path / "info"),
    )
    uid = "d" * 32
    path = storage._path(uid)
    lock_file = Path(storage.locks_dir) / f"{uid}.lock"

    held = threading.Event()
    release = threading.Event()

    def hold_lock():
        with acquire_upload_lock(path, locks_dir=storage.locks_dir, blocking=True):
            held.set()
            release.wait(timeout=5)

    holder = threading.Thread(target=hold_lock, daemon=True)
    holder.start()
    assert held.wait(timeout=2)

    async def scenario():
        async def waiter():
            async with storage.lock(uid):
                pass

        task = asyncio.create_task(waiter())
        # Give the worker thread a moment to enter acquire_upload_lock polling
        await asyncio.sleep(0.15)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        # Release the external lock; the cancelled enter_task will finish acquiring and must release
        release.set()
        holder.join(timeout=2)
        await asyncio.sleep(0.25)

        assert not lock_file.exists()
        # Verify lock can be acquired cleanly now
        async with storage.lock(uid):
            assert lock_file.exists()
        assert not lock_file.exists()

    asyncio.run(scenario())
