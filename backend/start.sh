#!/bin/bash
set -e

# Run database migrations
echo "Running Alembic migrations..."
alembic upgrade head

# Start the application, falling back to 8000 if PORT is not set
PORT="${PORT:-8000}"
echo "Starting Uvicorn on port $PORT..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
