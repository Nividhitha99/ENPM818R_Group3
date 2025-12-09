# ============================================================================
# API Gateway Service Dockerfile - Multi-Stage Build
# ============================================================================
# The gateway acts as the single entry point for all client requests,
# routing to appropriate backend services (auth, uploader, analytics, processor)
# Multi-stage build ensures minimal image size for faster deployments
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Build Stage - Python dependency installation
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Set working directory for build operations
WORKDIR /app

# Copy requirements file (separate layer for caching)
COPY requirements.txt .

# Install Python packages to isolated prefix
# Benefits: Clean separation, no build artifacts in final image
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ----------------------------------------------------------------------------
# Stage 2: Runtime Stage - Production-ready minimal image
# ----------------------------------------------------------------------------
FROM python:3.11-slim

# Set application working directory
WORKDIR /app

# Configure Python for optimal container performance
# PYTHONDONTWRITEBYTECODE: Prevents bytecode generation (reduces I/O)
# PYTHONUNBUFFERED: Ensures logs appear immediately in container logs
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Create non-privileged user (security hardening)
# Gateway service doesn't need root privileges
RUN useradd -m -u 1000 appuser

# Import only the installed dependencies from builder
# Excludes pip, wheel, setuptools from final image
COPY --from=builder /install /usr/local

# Copy gateway application code
COPY . .

# Set file ownership for non-root user
RUN chown -R appuser:appuser /app

# Drop root privileges before running application
USER appuser

# Expose gateway port for incoming traffic
EXPOSE 8000

# Health check for load balancers and orchestrators (ALB, Kubernetes)
# Verifies gateway can handle requests before routing traffic
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

# Launch FastAPI application via uvicorn
# Gateway handles routing, so no special uvicorn flags needed
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

