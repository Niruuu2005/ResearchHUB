FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Create non-root user and persistent storage directories
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data/documents /app/data/exports && \
    chown -R appuser:appuser /app
USER appuser

# Expose service port
EXPOSE 8000

# Healthcheck (Compose overrides start_period for slower first boot)
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (Compose may wrap with alembic upgrade)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
