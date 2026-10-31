# -*- coding: utf-8 -*-
import os
import tempfile
from BG_operations.LeaderElection import LeaderElection


def test_leader_election_single_process():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = os.path.join(tmpdir, "test_leader.lock")

        with LeaderElection.acquire(lock_file_path=lock_file) as leader:
            assert leader.is_leader is True
            assert os.path.exists(lock_file)

        # After releasing context manager
        assert leader.is_leader is False


def test_leader_election_multi_candidate():
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = os.path.join(tmpdir, "test_leader.lock")

        leader1 = LeaderElection.acquire(lock_file_path=lock_file)
        assert leader1.is_leader is True

        # Candidate 2 tries to acquire the same lock -> becomes follower
        follower = LeaderElection.acquire(lock_file_path=lock_file)
        assert follower.is_leader is False

        # Leader 1 releases
        leader1.release()
        assert leader1.is_leader is False

        # Now Candidate 2 can acquire
        leader2 = LeaderElection.acquire(lock_file_path=lock_file)
        assert leader2.is_leader is True
        leader2.release()
