#! /usr/bin/env sh
set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
exec uvicorn main:app --host 0.0.0.0