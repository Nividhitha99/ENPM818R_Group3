# Build Stage
FROM python:3.11-slim as builder

WORKDIR /app

# Upgrade pip to fix security vulnerabilities
RUN pip install --upgrade pip>=25.3

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime Stage
FROM python:3.11-slim

WORKDIR /app

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install curl for health checks and remove unnecessary packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create non-root user with minimal privileges
RUN useradd -m -u 1000 -s /sbin/nologin appuser

COPY --from=builder /install /usr/local
COPY . .

# Set proper permissions
RUN chown -R appuser:appuser /app && \
    chmod -R 755 /app

USER appuser

EXPOSE 8000

# Health check using curl (more reliable than Python)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--limit-max-requests", "1000", "--timeout-keep-alive", "300", "--limit-concurrency", "1000", "--limit-max-request-line", "8190", "--limit-max-request-headers", "32768"]