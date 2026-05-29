#!/bin/sh

set -e

echo "Waiting for database..."

until pg_isready -h db -U postgres; do
  sleep 2
done

echo "Database ready"

echo "Running migrations..."
alembic upgrade head

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload