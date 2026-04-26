# ============================================================
# Sk6.0 Backend — Production Dockerfile
# Multi-stage build: builder + slim runtime image
# Final image: python:3.12-slim, non-root user, no dev deps
# ============================================================

# ── Stage 1: Dependency Builder ──────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build tools (needed for some pip packages with C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies into a prefix directory
# This keeps the final image clean — only compiled wheels copied over
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime Image ───────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="Sk6.0 Engineering Team"
LABEL version="1.0"
LABEL description="Sk6.0 Lottery Platform — FastAPI Backend"

WORKDIR /app

# Runtime OS deps only (libpq for asyncpg, curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Create non-root user for security
# UID/GID 1001 — avoids conflicts with common system users
RUN groupadd -g 1001 sk6 \
    && useradd -u 1001 -g sk6 -s /bin/bash -m sk6 \
    && mkdir -p /app/static /app/logs \
    && chown -R sk6:sk6 /app

# Copy application source
COPY --chown=sk6:sk6 . /app

# Switch to non-root user
USER sk6

# Expose API port (internal only — Nginx proxies to this)
EXPOSE 8000

# Health check — FastAPI /health endpoint must return 200
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (overridden in docker-compose per service role)
CMD ["gunicorn", "app.main:app", \
     "-w", "2", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--timeout", "30", \
     "--graceful-timeout", "20", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
