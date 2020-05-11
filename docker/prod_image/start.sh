#! /usr/bin/env sh
set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
# 4 workers as each is blocking when not async
exec gunicorn -w 4 --bind=0.0.0.0 --worker-class uvicorn.workers.UvicornWorker main:app