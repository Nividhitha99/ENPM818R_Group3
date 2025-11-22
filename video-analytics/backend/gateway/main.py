from fastapi import FastAPI, Request, HTTPException
import httpx
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gateway")

app = FastAPI(title="API Gateway")

UPLOADER_URL = os.getenv("UPLOADER_SERVICE_URL", "http://uploader:8000")
ANALYTICS_URL = os.getenv("ANALYTICS_SERVICE_URL", "http://analytics:8000")
AUTH_URL = os.getenv("AUTH_SERVICE_URL", "http://auth:8000")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

async def proxy_request(url: str, method: str, headers: dict = None, data: bytes = None):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(method, url, headers=headers, content=data)
            return response.json() # Assuming JSON for simplicity
        except Exception as e:
            logger.error(f"Proxy error: {str(e)}")
            raise HTTPException(status_code=502, detail="Service Unavailable")

@app.post("/api/upload")
async def proxy_upload(request: Request):
    # For file uploads, proxying is tricky with simple httpx json. 
    # We'll just redirect or assume the client hits uploader directly in k8s via Ingress.
    # But for the sake of the aggregator pattern:
    return {"message": "Please upload directly to /uploader endpoint via Ingress"}

@app.get("/api/stats")
async def get_stats():
    return await proxy_request(f"{ANALYTICS_URL}/stats", "GET")

@app.post("/api/token")
async def login(request: Request):
    body = await request.body()
    # Forward raw body? Or parse?
    # Simplified:
    return {"message": "Auth via Gateway not fully implemented, use Auth service directly"}


