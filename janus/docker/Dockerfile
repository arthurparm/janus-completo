# syntax=docker/dockerfile:1
# --- Stage 1: Builder (with uv) ---
# Using python:3.11-slim-bookworm for a stable, small base
FROM python:3.11-slim-bookworm as builder

# Setup build environment
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install build dependencies and uv (much faster than pip/poetry)
# uv pip install is significantly faster and handles resolution better
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install system build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libstdc++6 \
    libgomp1 \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment using uv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy dependency files first (layer caching)
COPY pyproject.toml poetry.lock* ./

# Install dependencies using uv (adapter for poetry lock)
# We export poetry lock to requirements format on the fly or let uv handle it if compatible.
# Since uv supports legacy pip, we can use it to install from requirements.
# Ideally, we export requirements, but uv can also install pyproject.toml projects directly in newer versions.
# Let's use standard pip install via uv for reliability with poetry projects if uv sync isn't fully adopted yet.
# Actually, simpler: install poetry via uv, then export to requirements, then install with uv.
# OR: just use poetry but with uv as the installer if configured.
# FASTEST PATH: Export to requirements using a temporary poetry install, then install with uv.

RUN uv pip install poetry poetry-plugin-export && \
    if ! poetry export -f requirements.txt --output requirements.txt --without-hashes --no-interaction --no-ansi; then \
        poetry lock --no-interaction --no-ansi; \
        poetry export -f requirements.txt --output requirements.txt --without-hashes --no-interaction --no-ansi; \
    fi && \
    uv pip install -r requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.11-slim-bookworm as final

WORKDIR /app

# Create a non-root user with explicit UID 1000 for better bind-mount compatibility
RUN groupadd -g 1000 janus && useradd -u 1000 -g janus -m -d /home/janus -s /bin/bash janus
ENV HOME=/home/janus

# Install runtime system dependencies
# docker-ce-cli is needed for SysAdmin capabilities (bind mount socket)
# git is needed for semantic commits and code analysis features
RUN apt-get update && apt-get install -y --no-install-recommends \
    libstdc++6 \
    libgomp1 \
    libasound2 \
    libportaudio2 \
    curl \
    gnupg \
    lsb-release \
    git \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder --chown=janus:janus /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=janus:janus ./app ./app

# Create necessary directories with permissions
RUN mkdir -p /app/data /app/workspace /app/logs && \
    chown -R janus:janus /app/data /app/workspace /app/logs

# Use non-root user
USER janus

# Expose port
EXPOSE 8000

# Healthcheck is handled in docker-compose, but good practice to have here too
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Command is provided by docker-compose, but provide a safe default
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
