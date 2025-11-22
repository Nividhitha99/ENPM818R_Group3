from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import boto3
import os
import logging
from prometheus_client import make_asgi_app, Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analytics")

app = FastAPI(title="Analytics Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

VIEWS_COUNTER = Counter('video_views_total', 'Total video views')

dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=os.getenv("AWS_ENDPOINT_URL")
)

TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "video-metadata")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/stats")
def get_stats():
    try:
        table = dynamodb.Table(TABLE_NAME)
        # Scan is expensive, but okay for demo. In prod, use GSI or specific keys.
        response = table.scan(Limit=100)
        items = response.get('Items', [])
        return {"count": len(items), "items": items}
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/view/{video_id}")
def record_view(video_id: str):
    try:
        table = dynamodb.Table(TABLE_NAME)
        # Atomic increment
        table.update_item(
            Key={'video_id': video_id},
            UpdateExpression="set views = if_not_exists(views, :start) + :inc",
            ExpressionAttributeValues={
                ':start': 0,
                ':inc': 1
            },
            ReturnValues="UPDATED_NEW"
        )
        VIEWS_COUNTER.inc()
        return {"status": "view_recorded"}
    except Exception as e:
        logger.error(f"Error recording view: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

