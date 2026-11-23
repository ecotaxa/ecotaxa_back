#! /usr/bin/env sh
set -e
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
python3 run.py gunicorn &
GUNICORN_PID=$!
python3 run_bg_worker.py &
SCHEDULER_PID=$!

STOPPING=0
cleanup() {
    kill -TERM "$SCHEDULER_PID" "$GUNICORN_PID" 2>/dev/null || true
    wait "$SCHEDULER_PID" "$GUNICORN_PID" 2>/dev/null || true
}
on_signal() {
    STOPPING=1
    cleanup
    exit 0
}
trap on_signal TERM INT

while kill -0 "$SCHEDULER_PID" 2>/dev/null && kill -0 "$GUNICORN_PID" 2>/dev/null; do
    sleep 1 &
    wait $! 2>/dev/null || true
done

cleanup
if [ "$STOPPING" -eq 1 ]; then
    exit 0
fi
exit 1