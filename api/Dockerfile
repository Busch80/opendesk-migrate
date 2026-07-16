# opendesk-migrate API image

FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy

# Install system deps for cryptography, asyncpg, etc.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        libssl-dev \
        libffi-dev \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast, lockable)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (cache-friendly)
COPY api/requirements.txt ./requirements.txt
COPY api/alembic ./alembic
COPY api/alembic.ini ./alembic.ini
COPY api/app ./app

RUN uv pip install --system --no-cache -r requirements.txt 2>&1 | tail -30 || true

# Production image ----------------------------------------------------
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        libxml2 \
        libxslt1.1 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -r -s /sbin/nologin -u 10001 odmig

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source
COPY api/README.md ./README.md 2>/dev/null || true
COPY api/app ./app
COPY api/alembic ./alembic
COPY api/alembic.ini ./alembic.ini

RUN mkdir -p /staging && chown -R odmig:odmig /app /staging

USER odmig

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:8000/healthz || exit 1
