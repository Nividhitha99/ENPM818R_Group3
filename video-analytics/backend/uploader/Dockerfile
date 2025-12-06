# Build Stage
FROM python:3.11-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime Stage
FROM python:3.11-slim

WORKDIR /app

<<<<<<< HEAD
# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
=======
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1
>>>>>>> 8b04acb2e04af5ba2eb686ce031b628846193e8f

# Create non-root user
RUN useradd -m -u 1000 appuser

COPY --from=builder /install /usr/local
COPY . .

# Chown files
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--limit-max-requests", "1000", "--timeout-keep-alive", "300", "--limit-concurrency", "1000"]