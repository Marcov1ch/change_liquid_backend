FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    POETRY_VERSION=2.1.4 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --without dev --no-interaction

COPY src/ ./src/
COPY alembic/ ./alembic/

RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY docker-entrypoint.py /usr/local/bin/docker-entrypoint.py

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/openapi.json', timeout=3)"

ENTRYPOINT ["python", "/usr/local/bin/docker-entrypoint.py"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
