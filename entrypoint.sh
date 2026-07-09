#!/bin/sh
set -e

poetry run alembic upgrade head || {
    poetry run alembic stamp head && poetry run alembic upgrade head
}

exec poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
