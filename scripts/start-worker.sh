#!/bin/sh
set -eu

mkdir -p "$PROMETHEUS_MULTIPROC_DIR"
find "$PROMETHEUS_MULTIPROC_DIR" -maxdepth 1 -type f -name '*.db' -delete

exec python -m celery -A app.core.workers.celery worker --loglevel=info