# -*- coding: utf-8 -*-
import time
from pathlib import Path

from tests.api_wrappers import api_upload_file, api_remove_user_file
from tests.credentials import CREATOR_AUTH


LOCAL_BIG = "/home/laurent/Téléchargements/export_14819_20241129_0846.zip"


# To try on own env, rename notest_ below to test_ and fill LOCAL_BIG above
def notest_upload_perf(fastapi, tstlogs):
    """
    Measure performance of api_upload_file.
    """
    big_one = Path(LOCAL_BIG)
    file_name = big_one.name
    file_size_mb = big_one.stat().st_size

    remote_path = f"perf_tests/{file_name}"

    # Measure upload time
    start_time = time.time()
    api_upload_file(fastapi, str(big_one), remote_path, CREATOR_AUTH)
    end_time = time.time()

    duration = end_time - start_time
    throughput = file_size_mb / duration if duration > 0 else 0

    print(f"\nUpload of {file_size_mb}MB took {duration:.2f}s ({throughput:.2f} MB/s)")

    api_remove_user_file(fastapi, remote_path, CREATOR_AUTH)

    # Basic assertion to ensure it didn't take an astronomical amount of time
    assert duration < 60, f"Upload took too long: {duration:.2f}s"
