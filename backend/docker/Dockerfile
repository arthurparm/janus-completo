# syntax=docker/dockerfile:1.7
# --- Stage 1: Builder (with uv) ---
FROM python:3.11-slim as builder

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install build dependencies. Debian slim uses glibc/manylinux-compatible wheels,
# which are required by CUDA-related Python packages.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
    git \
    libgomp1 \
    portaudio19-dev && \
    rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN uv venv --seed /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy dependency files first (maximize layer cache)
COPY pyproject.toml poetry.lock* ./

# Install dependencies using uv with build cache
RUN --mount=type=cache,target=/root/.cache/uv,sharing=locked \
    --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    uv pip install poetry poetry-plugin-export && \
    if ! poetry export -f requirements.txt --output requirements.txt --without-hashes --no-interaction --no-ansi; then \
        poetry lock --no-interaction --no-ansi && \
        poetry export -f requirements.txt --output requirements.txt --without-hashes --no-interaction --no-ansi; \
    fi && \
    uv pip install -r requirements.txt

# --- Stage 2: Runtime Base ---
FROM python:3.11-slim as runtime-base

WORKDIR /app

# Create non-root user (UID 1000 for bind-mount compatibility)
RUN groupadd -g 1000 janus && \
    useradd -u 1000 -g janus -m -d /home/janus -s /bin/sh janus && \
    mkdir -p /app/data /app/workspace /app/logs && \
    chown -R janus:janus /app

ENV HOME=/home/janus

# Install runtime dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libstdc++6 \
    libgomp1 \
    libasound2 \
    libportaudio2 \
    git \
    curl \
    ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder --chown=janus:janus /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (late in build to maximize cache hits)
COPY --chown=janus:janus ./app ./app

USER janus

# --- Stage 3: Test Image ---
FROM runtime-base as test

USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/* && \
    /opt/venv/bin/python -m pip install --no-cache-dir pytest pytest-asyncio
USER janus

# --- Stage 4: Runtime Final (default) ---
FROM runtime-base as final

ARG JANUS_BUILD_REF=local-dev
ARG JANUS_BUILD_DATE
ARG JANUS_VERSION=0.5.44

# Install Docker CLI (SysAdmin capability)
USER root
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends docker.io tzdata && \
    rm -rf /var/lib/apt/lists/*

ENV JANUS_BUILD_REF=${JANUS_BUILD_REF}
ENV JANUS_BUILD_DATE=${JANUS_BUILD_DATE}
ENV JANUS_VERSION=${JANUS_VERSION}

LABEL org.opencontainers.image.revision=${JANUS_BUILD_REF} \
      org.opencontainers.image.created=${JANUS_BUILD_DATE} \
      org.opencontainers.image.version=${JANUS_VERSION}

USER janus

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
