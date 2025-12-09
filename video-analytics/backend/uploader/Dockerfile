# ============================================================================
# Uploader Service Dockerfile - Multi-Stage Build with High Concurrency
# ============================================================================
# This service handles video uploads to S3 with optimizations for:
# - High concurrency (1000 concurrent uploads)
# - Extended keep-alive for large file uploads (5 minutes)
# - Request limiting to prevent resource exhaustion
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Build Stage - Dependency layer
# ----------------------------------------------------------------------------
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies to isolated location
# Enables clean separation between build and runtime
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ----------------------------------------------------------------------------
# Stage 2: Runtime Stage - High-performance upload handler
# ----------------------------------------------------------------------------
FROM python:3.11-slim

# Set application directory
WORKDIR /app

# Python performance flags
# Optimized for file upload operations
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Create non-root user for security
# Upload service doesn't require root privileges
RUN useradd -m -u 1000 appuser

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy uploader service code
COPY . .

# Set ownership to application user
RUN chown -R appuser:appuser /app

# Run as non-privileged user
USER appuser

# Expose upload service port
EXPOSE 8000

# Health check for load balancer integration
# Verifies uploader can accept new upload requests
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--limit-max-requests", "1000", "--timeout-keep-alive", "300", "--limit-concurrency", "1000"]

