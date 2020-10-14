#! /usr/bin/env sh
set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
# 16 workers as each is blocking when not async
exec gunicorn -w 16 --threads 2 --bind=0.0.0.0 --timeout 600 --worker-class uvicorn.workers.UvicornWorker main:app
