# -*- coding: utf-8 -*-
import time
from unittest.mock import patch

from BG_operations.ResourceCleaner import ResourceCleaner


def _mock_cleaner_service():
    p1 = patch.object(ResourceCleaner, "__init__", lambda self: None)
    p2 = patch.object(ResourceCleaner, "__enter__", lambda self: self)
    p3 = patch.object(ResourceCleaner, "__exit__", lambda self, *args: None)
    return p1, p2, p3


def test_resource_cleaner_lifecycle():
    call_count = 0

    def mock_cleanup(self):
        nonlocal call_count
        call_count += 1

    p1, p2, p3 = _mock_cleaner_service()
    with p1, p2, p3, patch.object(ResourceCleaner, "do_cleanup", new=mock_cleanup):
        ResourceCleaner.launch_at_interval(0.05)
        try:
            assert ResourceCleaner.stop_event.is_set() is False
            assert ResourceCleaner.the_thread is not None
            assert ResourceCleaner.the_thread.is_alive() is True
            assert ResourceCleaner.the_thread.name == "ResourceCleanerThread"

            # Wait enough for at least 2 cleanup cycles
            time.sleep(0.18)
            assert call_count >= 2
        finally:
            ResourceCleaner.shutdown()

        assert ResourceCleaner.stop_event.is_set() is True
        assert ResourceCleaner.the_thread is None


def test_resource_cleaner_no_duplicate_threads():
    p1, p2, p3 = _mock_cleaner_service()
    with p1, p2, p3, patch.object(ResourceCleaner, "do_cleanup", return_value=None):
        ResourceCleaner.launch_at_interval(0.1)
        try:
            first_thread = ResourceCleaner.the_thread
            assert first_thread is not None
            assert first_thread.is_alive() is True

            # Launch again with active thread should be a no-op
            ResourceCleaner.launch_at_interval(0.1)
            assert ResourceCleaner.the_thread is first_thread
        finally:
            ResourceCleaner.shutdown()

        assert ResourceCleaner.the_thread is None


def test_resource_cleaner_exception_resilience():
    call_count = 0

    def flaky_cleanup(self):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Transient cleanup failure")

    p1, p2, p3 = _mock_cleaner_service()
    with p1, p2, p3, patch.object(ResourceCleaner, "do_cleanup", new=flaky_cleanup):
        ResourceCleaner.launch_at_interval(0.05)
        try:
            time.sleep(0.18)
            assert call_count >= 2
            assert ResourceCleaner.the_thread is not None
            assert ResourceCleaner.the_thread.is_alive() is True
        finally:
            ResourceCleaner.shutdown()

        assert ResourceCleaner.the_thread is None


def test_resource_cleaner_shutdown_when_not_started():
    ResourceCleaner.shutdown()
    assert ResourceCleaner.the_thread is None
    assert ResourceCleaner.stop_event.is_set() is True
