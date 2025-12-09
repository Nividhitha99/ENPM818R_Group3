# ============================================================================
# Analytics Service Dockerfile - Multi-Stage Build
# ============================================================================
# This Dockerfile uses a multi-stage build pattern to:
# 1. Reduce final image size by excluding build dependencies
# 2. Improve security by minimizing attack surface
# 3. Optimize layer caching for faster rebuilds
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Build Stage - Install Python dependencies in isolated layer
# ----------------------------------------------------------------------------
# Using slim variant reduces image size while providing necessary build tools
FROM python:3.11-slim as builder

# Set working directory for the build stage
WORKDIR /app

# Copy only requirements first to leverage Docker layer caching
# If requirements.txt doesn't change, this layer will be reused
COPY requirements.txt .

# Install dependencies to /install prefix (isolated from system Python)
# --no-cache-dir: Prevents pip from caching packages, reducing image size
# --prefix=/install: Install to custom location for easy copying to runtime stage
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ----------------------------------------------------------------------------
# Stage 2: Runtime Stage - Minimal production image
# ----------------------------------------------------------------------------
# Start fresh from base image (excludes build tools and pip cache)
FROM python:3.11-slim

# Set working directory for the application
WORKDIR /app

# Python environment optimization flags
# PYTHONDONTWRITEBYTECODE=1: Prevents Python from writing .pyc files (reduces disk I/O)
# PYTHONUNBUFFERED=1: Forces stdout/stderr streams to be unbuffered (better logging in containers)
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Create non-root user for security (principle of least privilege)
# -m: Create home directory
# -u 1000: Explicit UID for consistency across environments
RUN useradd -m -u 1000 appuser

# Copy installed dependencies from builder stage (only what's needed)
# This excludes pip, setuptools, and build artifacts
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Set ownership to non-root user for all application files
RUN chown -R appuser:appuser /app

# Switch to non-root user (container won't run as root)
USER appuser

# Expose port 8000 for the FastAPI application
EXPOSE 8000

# Health check configuration for container orchestration (Kubernetes/ECS)
# --interval=30s: Check every 30 seconds
# --timeout=10s: Fail if check takes longer than 10 seconds
# --start-period=10s: Grace period before first check
# --retries=3: Mark unhealthy after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

# Start the FastAPI application using uvicorn ASGI server
# --host 0.0.0.0: Listen on all network interfaces
# --port 8000: Application port
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

