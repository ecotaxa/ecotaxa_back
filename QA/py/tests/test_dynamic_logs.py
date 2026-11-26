# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
import gc
import io
import logging
import threading
import weakref
from pathlib import Path

from helpers import DynamicLogs
from helpers.DynamicLogs import (
    LogEmitter,
    LogsSwitcher,
    PerThreadHandler,
    get_logger,
    rewire_loggers_after_fork,
)


class _DummyEmitter(LogEmitter):
    def __init__(self, paths):
        super().__init__()
        self._paths = list(paths)

    def log_file_path(self) -> str:
        val = self._paths.pop(0)
        if isinstance(val, Exception):
            raise val
        return val


def _make_record(msg: str = "hello") -> logging.LogRecord:
    return logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )


def test_per_thread_handler_switch_to_closes_previous_handler(tmp_path: Path):
    base_stream = io.StringIO()
    handler = PerThreadHandler(logging.StreamHandler(base_stream))
    file1 = tmp_path / "one.log"
    file2 = tmp_path / "two.log"

    handler.switch_to(str(file1))
    first_fh = handler._local.alt_handler
    assert isinstance(first_fh, logging.FileHandler)
    assert first_fh.stream is not None

    handler.switch_to(str(file2))
    assert first_fh.stream is None, "Previous FileHandler was not closed on overwrite"

    second_fh = handler._local.alt_handler
    assert isinstance(second_fh, logging.FileHandler)
    assert second_fh is not first_fh
    assert second_fh.stream is not None

    handler.emit(_make_record("msg2"))
    handler.stop_switch()
    assert second_fh.stream is None
    assert getattr(handler._local, "alt_handler", None) is None
    assert len(handler._active_handlers) == 0
    assert "msg2" in file2.read_text()
    assert "msg2" not in file1.read_text()


def test_per_thread_handler_concurrent_switch_and_emit(tmp_path: Path):
    base_stream = io.StringIO()
    handler = PerThreadHandler(logging.StreamHandler(base_stream))
    errors = []

    def worker(idx: int):
        try:
            log_file = tmp_path / f"worker_{idx}.log"
            for i in range(10):
                handler.switch_to(str(log_file))
                handler.emit(_make_record(f"w{idx}-{i}"))
            handler.stop_switch()
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(handler._active_handlers) == 0
    assert getattr(handler._local, "alt_handler", None) is None


def test_logs_switcher_exit_when_log_file_path_raises(tmp_path: Path):
    log_file = tmp_path / "job_raise.log"
    emitter = _DummyEmitter([str(log_file), RuntimeError("db gone")])

    with LogsSwitcher(emitter):
        logging.getLogger("test.raise").info("inside")

    assert getattr(DynamicLogs._the_handler._local, "alt_handler", None) is None
    assert len(DynamicLogs._the_handler._active_handlers) == 0


def test_logs_switcher_exit_when_log_file_path_becomes_falsy(tmp_path: Path):
    log_file = tmp_path / "job_falsy.log"
    emitter = _DummyEmitter([str(log_file), ""])

    with LogsSwitcher(emitter):
        pass

    assert getattr(DynamicLogs._the_handler._local, "alt_handler", None) is None
    assert len(DynamicLogs._the_handler._active_handlers) == 0


def test_per_thread_handler_thread_local_isolation(tmp_path: Path):
    base_stream = io.StringIO()
    handler = PerThreadHandler(logging.StreamHandler(base_stream))
    worker_file = tmp_path / "worker_only.log"
    entered = threading.Event()
    proceed = threading.Event()

    def worker():
        handler.switch_to(str(worker_file))
        entered.set()
        proceed.wait(timeout=5)
        handler.emit(_make_record("from_worker"))
        handler.stop_switch()

    t = threading.Thread(target=worker)
    t.start()
    entered.wait(timeout=5)

    # Main thread has no alt_handler and still logs to base_stream
    assert getattr(handler._local, "alt_handler", None) is None
    handler.emit(_make_record("from_main"))

    proceed.set()
    t.join()

    assert "from_main" in base_stream.getvalue()
    assert "from_main" not in worker_file.read_text()
    assert "from_worker" in worker_file.read_text()
    assert "from_worker" not in base_stream.getvalue()


def test_per_thread_handler_dead_thread_releases_handler(tmp_path: Path):
    base_stream = io.StringIO()
    handler = PerThreadHandler(logging.StreamHandler(base_stream))
    leaked_file = tmp_path / "dead_thread.log"
    fh_refs: list[weakref.ref[logging.FileHandler]] = []

    def dying_worker():
        fh = handler.switch_to(str(leaked_file))
        assert isinstance(fh, logging.FileHandler)
        fh_refs.append(weakref.ref(fh))
        # Intentionally exit without stop_switch()

    t = threading.Thread(target=dying_worker)
    t.start()
    t.join()
    del t
    gc.collect()

    assert len(fh_refs) == 1
    assert fh_refs[0]() is None
    assert len(handler._active_handlers) == 0


def test_rewire_loggers_after_fork_closes_removed_handlers(tmp_path: Path):
    root_file = tmp_path / "root_extra.log"
    child_file = tmp_path / "child_extra.log"
    alt_file = tmp_path / "alt_before_fork.log"

    root_fh = logging.FileHandler(str(root_file))
    child_fh = logging.FileHandler(str(child_file))

    logging.getLogger().addHandler(root_fh)
    child_logger = get_logger("test.rewire.child")
    child_logger.addHandler(child_fh)
    DynamicLogs._the_handler.switch_to(str(alt_file))
    alt_fh = DynamicLogs._the_handler._local.alt_handler
    assert isinstance(alt_fh, logging.FileHandler)

    try:
        rewire_loggers_after_fork()
        assert root_fh.stream is None
        assert child_fh.stream is None
        assert alt_fh.stream is None
    finally:
        # Ensure clean state for any subsequent tests
        rewire_loggers_after_fork()
