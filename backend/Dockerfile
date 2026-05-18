FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed for psycopg and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for layer caching
COPY pyproject.toml ./

# Install the package in non-editable mode with all extras
RUN pip install --no-cache-dir --upgrade pip

# Copy application source
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/

# Install the package in editable mode to ensure module discovery
RUN pip install --no-cache-dir -e .[dev]

# Create a non-root user
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENV PYTHONPATH=/app/src

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "onepilot.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
