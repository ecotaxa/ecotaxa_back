#! /usr/bin/env sh
set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
LD_LIBRARY_PATH=/usr/local/cuda-11.4/compat/ exec python3 gpu_jobs_runner.py
