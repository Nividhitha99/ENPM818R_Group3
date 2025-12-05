import json
import logging
import os
import uuid
from datetime import datetime

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from prometheus_client import Counter, Histogram, make_asgi_app

app = FastAPI(title="API Gateway")


# Structured JSON Logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "gateway",
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "target"):
            log_data["target"] = record.target
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        return json.dumps(log_data)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("gateway")
logger.setLevel(logging.INFO)
logger.handlers = [handler]
logger.propagate = False

logging.getLogger("uvicorn").handlers = []
logging.getLogger("uvicorn.access").handlers = []
logging.getLogger("httpx").setLevel(logging.WARNING)


# Configuration
UPLOADER_URL = os.getenv("UPLOADER_SERVICE_URL", "http://uploader:8000")
ANALYTICS_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics:8000")
AUTH_URL = os.getenv("AUTH_SERVICE_URL", "http://auth:8000")
REQUEST_TIMEOUT = float(os.getenv("GATEWAY_TIMEOUT_SECONDS", "15"))


# Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

REQUEST_COUNTER = Counter("gateway_requests_total", "Gateway requests", ["endpoint", "method", "status_code"])
REQUEST_LATENCY = Histogram("gateway_request_latency_seconds", "Gateway latency", ["endpoint", "method"], buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10))
GATEWAY_ERRORS = Counter("gateway_errors_total", "Gateway errors", ["endpoint", "reason"])


def get_correlation_id(request: Request) -> str:
    return request.headers.get("X-Correlation-ID") or str(uuid.uuid4())


def enrich_headers(request: Request, correlation_id: str) -> dict:
    headers = dict(request.headers)
    headers["X-Correlation-ID"] = correlation_id
    return headers


async def forward(request: Request, target_url: str, method: str = "GET", allow_json: bool = True):
    correlation_id = get_correlation_id(request)
    endpoint = request.url.path
    start = datetime.utcnow()
    body = await request.body()
    headers = enrich_headers(request, correlation_id)

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            resp = await client.request(method, target_url, content=body, headers=headers)
            status_code = resp.status_code
            REQUEST_COUNTER.labels(endpoint=endpoint, method=method, status_code=status_code).inc()
            if resp.headers.get("content-type", "").startswith("application/json") and allow_json:
                content = resp.json()
            else:
                content = resp.text
            log_with_context(logging.INFO, "proxy_success", correlation_id, path=endpoint, target=target_url, status_code=status_code)
            return Response(content=json.dumps(content) if allow_json else content, status_code=status_code, media_type="application/json" if allow_json else resp.headers.get("content-type", "application/octet-stream"))
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            REQUEST_COUNTER.labels(endpoint=endpoint, method=method, status_code=status_code).inc()
            GATEWAY_ERRORS.labels(endpoint=endpoint, reason=str(exc)).inc()
            log_with_context(logging.WARNING, f"proxy_http_error: {exc}", correlation_id, path=endpoint, target=target_url, status_code=status_code)
            raise HTTPException(status_code=status_code, detail="Upstream error")
        except Exception as exc:
            REQUEST_COUNTER.labels(endpoint=endpoint, method=method, status_code=502).inc()
            GATEWAY_ERRORS.labels(endpoint=endpoint, reason="exception").inc()
            log_with_context(logging.ERROR, f"proxy_exception: {exc}", correlation_id, path=endpoint, target=target_url)
            raise HTTPException(status_code=502, detail="Service Unavailable")
        finally:
            duration = (datetime.utcnow() - start).total_seconds()
            REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)


def log_with_context(level, message, correlation_id=None, path=None, target=None, status_code=None):
    record = logging.LogRecord(
        name="gateway",
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    if correlation_id:
        record.correlation_id = correlation_id
    if path:
        record.path = path
    if target:
        record.target = target
    if status_code:
        record.status_code = status_code
    logger.handle(record)


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Analytics routes
@app.get("/api/analytics/videos")
async def list_videos(request: Request):
    target = f"{ANALYTICS_URL}/videos{('?' + str(request.url.query)) if request.url.query else ''}"
    return await forward(request, target, method="GET")


@app.get("/api/analytics/video/{video_id}")
async def get_video(video_id: str, request: Request):
    target = f"{ANALYTICS_URL}/video/{video_id}"
    return await forward(request, target, method="GET")


@app.get("/api/analytics/stats")
async def get_stats(request: Request):
    target = f"{ANALYTICS_URL}/stats"
    return await forward(request, target, method="GET")


@app.post("/api/analytics/view/{video_id}")
async def record_view(video_id: str, request: Request):
    target = f"{ANALYTICS_URL}/view/{video_id}"
    return await forward(request, target, method="POST")


@app.post("/api/analytics/like/{video_id}")
async def record_like(video_id: str, request: Request):
    target = f"{ANALYTICS_URL}/like/{video_id}"
    return await forward(request, target, method="POST")


# Uploader route (stream body as-is)
@app.post("/api/uploader/upload")
async def upload(request: Request):
    target = f"{UPLOADER_URL}/upload"
    return await forward(request, target, method="POST")


# Auth proxy
@app.post("/api/auth/token")
async def auth_token(request: Request):
    target = f"{AUTH_URL}/token"
    return await forward(request, target, method="POST")


@app.get("/api/auth/verify")
async def auth_verify(request: Request):
    target = f"{AUTH_URL}/verify"
    return await forward(request, target, method="GET")


