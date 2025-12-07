# ============================================================================
# Processor Service Dockerfile - Multi-Stage Build with Video Processing
# ============================================================================
# This service performs video processing tasks using FFmpeg
# Requirements:
# - Multi-stage build to separate build deps from runtime deps
# - FFmpeg for video transcoding and analysis
# - Non-root execution for security
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Build Stage - Python dependencies installation
# ----------------------------------------------------------------------------
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Copy requirements for dependency caching
COPY requirements.txt .

# Install Python packages to custom prefix
# Isolates packages for clean transfer to runtime stage
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ----------------------------------------------------------------------------
# Stage 2: Runtime Stage - Video processing environment
# ----------------------------------------------------------------------------
FROM python:3.11-slim

# Set application directory
WORKDIR /app

# Python environment optimization
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

# Install FFmpeg for video processing capabilities
# --no-install-recommends: Install only essential packages
# apt-get clean && rm -rf: Remove package lists to reduce image size
# FFmpeg is required for video transcoding, thumbnail generation, and format conversion
RUN apt-get update && \
  apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user for running the service
# Video processing doesn't require elevated privileges
RUN useradd -m -u 1000 appuser

# Copy Python dependencies from builder stage
COPY --from=builder /install /usr/local

# Copy processor service code
COPY . .

# Transfer file ownership to application user
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose service port
EXPOSE 8000

# Health check for container orchestration
# Ensures processor is ready to accept video processing jobs
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

# Start the processor service
# Handles SQS messages and processes videos using FFmpeg
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

