#!/usr/bin/env bash
set -e

# ROLE must be set in env (leader or follower)
if [ -z "$ROLE" ]; then
  echo "ROLE environment variable not set (leader|follower)"
  exit 1
fi

PORT=${PORT:-8000}
export HOST=0.0.0.0

echo "Starting $ROLE on port $PORT ..."
python -m uvicorn app.${ROLE}:app --host 0.0.0.0 --port ${PORT} --workers 1
