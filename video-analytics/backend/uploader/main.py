from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import boto3
import os
import uuid
import json
import logging
from prometheus_client import make_asgi_app, Counter, Histogram

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uploader")

app = FastAPI(title="Uploader Service")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

UPLOAD_COUNTER = Counter('video_uploads_total', 'Total number of video uploads')
UPLOAD_LATENCY = Histogram('video_upload_latency_seconds', 'Latency of video uploads')

# AWS Clients
s3_client = boto3.client(
    's3',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=os.getenv("AWS_ENDPOINT_URL") # For localstack if needed
)
sqs_client = boto3.client(
    'sqs',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=os.getenv("AWS_ENDPOINT_URL")
)

BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "video-uploads")
QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split(".")[-1]
        s3_key = f"{file_id}.{file_extension}"
        
        logger.info(f"Starting upload for {file.filename} as {s3_key}")

        # Upload to S3
        with UPLOAD_LATENCY.time():
            s3_client.upload_fileobj(file.file, BUCKET_NAME, s3_key)
        
        # Send message to SQS
        message = {
            "video_id": file_id,
            "s3_bucket": BUCKET_NAME,
            "s3_key": s3_key,
            "original_filename": file.filename
        }
        
        sqs_client.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message)
        )
        
        UPLOAD_COUNTER.inc()
        logger.info(f"Upload complete and job queued for {file_id}")
        
        return {
            "status": "success",
            "video_id": file_id,
            "message": "Video uploaded and processing started"
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

