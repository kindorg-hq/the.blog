# The image ci builds and ships is the last stage (`runtime`): the app and
# Poetry's main group, nothing else. `dev` is that image plus the dev group
# (pytest, pytest-django) for the tests and local development; it never ships.

# What `dev` is built on: this Dockerfile's `runtime` stage, unless set.
# compose.test.yml sets it to the image under test (IMAGE_BLOG, the one ci
# built), so the tests run on the shipped image with only the dev group added.
ARG IMAGE_BLOG=runtime

# ============== Requirements ==============
# Poetry only exports the locked deps, one file per group. It gets its own
# venv in its own stage, so it and its own deps (not in poetry.lock) never
# reach an image.
FROM python:3.14-slim AS requirements

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/poetry \
    && /opt/poetry/bin/pip install --no-cache-dir poetry==2.3.4 poetry-plugin-export==1.9.0

WORKDIR /src
COPY pyproject.toml poetry.lock ./
RUN mkdir /requirements \
    && /opt/poetry/bin/poetry export --only main --without-hashes -f requirements.txt -o /requirements/main.txt \
    && /opt/poetry/bin/poetry export --only dev --without-hashes -f requirements.txt -o /requirements/dev.txt


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

# Isolated venv outside /app so dev bind-mounts don't shadow it; the runtime
# stage copies it, so it holds exactly poetry.lock's main group.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=requirements /requirements/main.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

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


# ============== Dev ==============
# IMAGE_BLOG (`runtime` by default) plus the dev group, nothing else: --no-deps
# so pip changes no package the image already has. Not named `test`: ci runs a
# `test` stage inside `docker build`, where there is no Postgres; these tests
# run from compose.test.yml instead.
FROM ${IMAGE_BLOG} AS dev

USER root
COPY --from=requirements /requirements/dev.txt /tmp/requirements-dev.txt
RUN pip install --no-cache-dir --no-deps --disable-pip-version-check -r /tmp/requirements-dev.txt \
    && rm /tmp/requirements-dev.txt
USER app


# ============== The image ==============
# The last stage is what ci builds and ships: `runtime`, as is.
FROM runtime
