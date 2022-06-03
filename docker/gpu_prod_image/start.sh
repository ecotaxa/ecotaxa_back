#! /usr/bin/env sh
set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
exec python3 gpu_jobs_runner.py
