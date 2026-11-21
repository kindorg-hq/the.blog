# ============== Builder ==============
FROM python:3.14-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Poetry only exports the locked deps. It gets its own venv, outside /opt/venv,
# so it and its own deps (not in poetry.lock) stay in the builder stage.
RUN python -m venv /opt/poetry \
    && /opt/poetry/bin/pip install --no-cache-dir poetry==2.3.4 poetry-plugin-export==1.9.0

# Isolated venv outside /app so dev bind-mounts don't shadow it; the runtime
# stage copies it, so it holds exactly what poetry.lock lists.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN /opt/poetry/bin/poetry export --with dev --without-hashes -f requirements.txt -o /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput


# ============== Runtime ==============
FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq5 \
        make \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r app && useradd -r -g app -d /app -s /bin/sh app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=app:app /app /app

USER app

CMD ["make", "docker-run-production"]
