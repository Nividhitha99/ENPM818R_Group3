# ============================================================================
# Auth Service Dockerfile - Multi-Stage Build with Security Hardening
# ============================================================================
# This service handles JWT authentication and requires enhanced security:
# - Multi-stage build reduces attack surface
# - Non-root user execution
# - Extended keep-alive timeout for long-lived auth sessions
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Build Stage - Dependency installation layer
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Set working directory
WORKDIR /app

# Copy requirements for layer caching optimization
COPY requirements.txt .

# Install dependencies to isolated prefix
# This allows us to copy only installed packages to runtime stage
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ----------------------------------------------------------------------------
# Stage 2: Runtime Stage - Secure production environment
# ----------------------------------------------------------------------------
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Python optimization environment variables
# PYTHONDONTWRITEBYTECODE: Skip .pyc file generation
# PYTHONUNBUFFERED: Enable real-time log output
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Create dedicated non-root user (security best practice)
RUN useradd -m -u 1000 appuser

# Copy only installed packages from builder (excludes build tools)
COPY --from=builder /install /usr/local

# Copy application source code
COPY . .

# Transfer ownership to non-root user
RUN chown -R appuser:appuser /app

# Run as non-root user (prevents privilege escalation)
USER appuser

# Expose application port
EXPOSE 8000

# Container health monitoring for orchestrators
# Ensures service is responding to HTTP requests
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

# Start uvicorn with extended keep-alive for auth sessions
# --timeout-keep-alive 120: Keep connections alive for 2 minutes (auth sessions)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "120"]
