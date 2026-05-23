# syntax=docker/dockerfile:1.6

# --- builder ---
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# system deps for asyncpg / psycopg
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip \
 && pip install .

# --- runtime ---
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
 && apt-get install -y --no-install-recommends libpq5 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY src /app/src
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations

ENV PYTHONPATH=/app/src

EXPOSE 8000
ENTRYPOINT ["uvicorn", "gecko_vpp.main:app", "--host", "0.0.0.0", "--port", "8000"]
