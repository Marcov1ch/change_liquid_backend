FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root --without dev

COPY .env alembic.ini ./
COPY alembic/ ./alembic/
COPY src/ ./src/

ENV PYTHONPATH=/app/src

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]