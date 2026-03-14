# ─── Stage 1: Builder ────────────────────────────────────────────────────────
# Installs dependencies into a virtual environment using uv.
FROM python:3.12-slim AS builder

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency manifest first for layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies (no dev extras) into /app/.venv
RUN uv sync --frozen --no-install-project --no-dev

# ─── Stage 2: Runtime ────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY app/ ./app/

# Activate the virtual environment by prepending it to PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Run as a non-root user for security
RUN groupadd --system appuser && useradd --system --gid appuser appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# ─── FastAPI App ──────────────────────────────────────────────────────────────
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
