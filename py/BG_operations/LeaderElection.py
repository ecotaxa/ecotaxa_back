# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2026  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Leader election using file locking mechanism (fcntl.flock)
# Ensures exactly one worker process becomes the leader among gunicorn/uvicorn workers

import errno
import fcntl
import logging
import os
import tempfile
import time
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Default lock file name
DEFAULT_LOCK_FILENAME = "/tmp/ecotaxa_leader.lock"

# Lock name for logging
LOCK_NAME = "ecotaxa_leader_election"


def get_default_lock_file() -> str:
    """
    Get the default path for the leader election lock file.

    Priority:
    1. LEADER_LOCK_FILE environment variable
    2. config.jobs_dir() / "ecotaxa_leader.lock" if accessible
    3. tempfile.gettempdir() / "ecotaxa_leader.lock"
    """
    env_path = os.environ.get("LEADER_LOCK_FILE")
    if env_path:
        return env_path

    try:
        from API_operations.helpers.Service import Service
        from helpers.AppConfig import Config

        config = Service.the_config or Config()
        jobs_dir = config.jobs_dir()
        if jobs_dir and os.path.exists(jobs_dir):
            return os.path.join(jobs_dir, DEFAULT_LOCK_FILENAME)
    except Exception:
        pass

    return os.path.join(tempfile.gettempdir(), DEFAULT_LOCK_FILENAME)


class LeaderElectionError(Exception):
    """Raised when leader election fails."""

    pass


class LeaderElection:
    """
    Leader election mechanism using OS file locking (fcntl.flock).

    This ensures exactly one worker process becomes the leader. The lock is
    process-scoped and kernel-managed, so it's automatically released when
    the process closes the file descriptor or terminates/crashes, preventing deadlocks.

    Usage:
        with LeaderElection.acquire() as leader_election:
            if leader_election.is_leader:
                # This process is the leader
                start_leader_tasks()
            else:
                # This process is a follower
                pass
    """

    def __init__(self) -> None:
        self._is_leader: Optional[bool] = None
        self._fd: Optional[int] = None
        self._lock_acquired = False

    @classmethod
    def get_lock_file_path(cls) -> str:
        """
        Get the lock file path used for leader election.

        Returns:
            str: Path to the lock file
        """
        return get_default_lock_file()

    @classmethod
    def acquire(
        cls,
        lock_file_path: Optional[str] = None,
        lock_name: str = LOCK_NAME,
    ) -> "LeaderElection":
        """
        Create and acquire a leader election lock using file locking.

        Args:
            lock_file_path: Optional path to lock file (uses default if None)
            lock_name: Name for logging purposes

        Returns:
            LeaderElection instance with is_leader set

        Raises:
            LeaderElectionError: If lock acquisition encounters an unexpected fatal error
        """
        target_path = lock_file_path or cls.get_lock_file_path()
        election = cls()

        try:
            # Ensure parent directory exists
            lock_dir = os.path.dirname(os.path.abspath(target_path))
            if lock_dir and not os.path.exists(lock_dir):
                os.makedirs(lock_dir, exist_ok=True)

            # Open file for read/write
            fd = os.open(target_path, os.O_CREAT | os.O_RDWR, 0o666)
            election._fd = fd

            # Attempt non-blocking exclusive lock
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_acquired = True
            except (BlockingIOError, OSError) as lock_err:
                if lock_err.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES):
                    lock_acquired = False
                else:
                    raise

            election._is_leader = lock_acquired
            election._lock_acquired = lock_acquired

            pid = election._get_pid()

            if election._is_leader:
                # Write current owner metadata into lock file
                try:
                    os.ftruncate(fd, 0)
                    os.lseek(fd, 0, os.SEEK_SET)
                    metadata = (
                        f"pid={pid}\n"
                        f"acquired_at={time.time()}\n"
                        f"lock_name={lock_name}\n"
                    )
                    os.write(fd, metadata.encode("utf-8"))
                    os.fsync(fd)
                except Exception as write_err:
                    logger.warning(
                        "Could not write leader metadata to lock file %s: %s",
                        target_path,
                        write_err,
                    )

                logger.info(
                    "Leader election: Worker acquired leader file lock '%s' at '%s'",
                    lock_name,
                    target_path,
                )
            else:
                # Close the file descriptor for follower
                try:
                    os.close(fd)
                except Exception:
                    pass
                election._fd = None

                logger.info(
                    "Leader election: Worker is follower (file lock '%s' held by another process)",
                    target_path,
                )

            return election

        except Exception as e:
            if election._fd is not None:
                try:
                    os.close(election._fd)
                except Exception:
                    pass
                election._fd = None

            logger.error(
                "Leader election failed : %s",
                str(e),
                exc_info=True,
            )
            raise LeaderElectionError(f"Failed to acquire leader lock: {e}") from e

    def __enter__(self) -> "LeaderElection":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - release lock."""
        self.release()

    def release(self) -> None:
        """
        Release the leader file lock and close file descriptor.
        """
        try:
            if self._fd is not None:
                if self._lock_acquired:
                    try:
                        fcntl.flock(self._fd, fcntl.LOCK_UN)
                    except Exception as e:
                        logger.debug("Error unlocking file lock: %s", e)

                try:
                    os.close(self._fd)
                except Exception as e:
                    logger.debug("Error closing lock file descriptor: %s", e)

                self._fd = None
                self._lock_acquired = False

                if self._is_leader:
                    logger.info(
                        "Leader lock released by worker",
                    )
                self._is_leader = False
        except Exception as e:
            logger.error(
                "Error releasing leader lock for worker: %s",
                str(e),
                exc_info=True,
            )

    @property
    def is_leader(self) -> bool:
        """
        Check if this process became the leader.

        Returns:
            bool: True if this process acquired the leader lock, False otherwise
        """
        return self._is_leader if self._is_leader is not None else False

    @staticmethod
    def _get_pid() -> str:
        """Get process ID for logging."""
        return str(os.getpid())
