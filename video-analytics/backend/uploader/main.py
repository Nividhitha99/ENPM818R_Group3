from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import boto3
import os
import uuid
import json
import time
import logging
from prometheus_client import make_asgi_app, Counter, Histogram
from botocore.exceptions import ClientError, BotoCoreError

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

# Task 1: Increase FastAPI/Uvicorn upload size limit
class MaxUploadSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to increase upload size limit to 500MB"""
    async def dispatch(self, request: Request, call_next):
        request.scope["client_max_size"] = 1024 * 1024 * 500  # 500MB
        return await call_next(request)

app.add_middleware(MaxUploadSizeMiddleware)

# Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

UPLOAD_COUNTER = Counter('video_uploads_total', 'Total number of video uploads')
UPLOAD_LATENCY = Histogram('video_upload_latency_seconds', 'Latency of video uploads')

# AWS Clients - Real AWS (endpoint_url=None) or LocalStack (if AWS_ENDPOINT_URL is set)
endpoint_url = os.getenv("AWS_ENDPOINT_URL")  # None for real AWS, URL for LocalStack
s3_client = boto3.client(
    's3',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=endpoint_url if endpoint_url else None
)
sqs_client = boto3.client(
    'sqs',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=endpoint_url if endpoint_url else None
)

BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "video-analytics-uploads")
QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")

# S3 supports large files, but we'll set a reasonable limit
MAX_FILE_SIZE = 1024 * 1024 * 500  # 500MB

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """
    Upload video file to S3 and metadata to S3.
    Videos stored in S3, metadata stored as JSON in S3.
    Uses streaming upload (no memory buffering).
    """
    file_id = None
    s3_video_key = None
    
    try:
        # Get file size for validation and logging
        file_size = 0
        try:
            if hasattr(file, 'size') and file.size:
                file_size = file.size
            elif hasattr(file.file, 'seek') and hasattr(file.file, 'tell'):
                current_pos = file.file.tell()
                file.file.seek(0, 2)  # Seek to end
                file_size = file.file.tell()
                file.file.seek(current_pos)  # Reset to original position
            else:
                file_size = getattr(file.file, 'spool_max_size', 0)
        except Exception as e:
            logger.warning(f"Could not determine file size: {str(e)}")
            file_size = 0
        
        # File size validation (500MB limit)
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"File {file.filename} exceeds 500MB limit: {file_size} bytes")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Maximum file size is 500MB. File size: {file_size} bytes."
            )
        
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "mp4"
        s3_video_key = f"videos/{file_id}.{file_extension}"
        
        logger.info(f"Starting upload: filename={file.filename}, size={file_size} bytes, video_id={file_id}")
        
        # Store video file in S3 (streaming upload - no memory buffering)
        with UPLOAD_LATENCY.time():
            try:
                # Reset file pointer to beginning for streaming
                file.file.seek(0)
                s3_client.upload_fileobj(
                    file.file,  # File-like object that streams
                    BUCKET_NAME,
                    s3_video_key,
                    ExtraArgs={'ContentType': file.content_type or 'video/mp4'}
                )
                logger.info(f"Video stored in S3: s3://{BUCKET_NAME}/{s3_video_key}, size={file_size} bytes")
            except ClientError as e:
                logger.error(f"S3 video upload failed for {file_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Upload failed. Please try again."
                )
            except BotoCoreError as e:
                logger.error(f"BotoCore error during upload for {file_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Upload failed. Please try again."
                )
        
        # Store metadata in S3
        timestamp = int(time.time())
        metadata = {
            "video_id": file_id,
            "filename": file.filename,
            "original_filename": file.filename,  # Keep for backward compatibility
            "file_extension": file_extension,
            "content_type": file.content_type or 'video/mp4',
            "size": file_size,
            "file_size": file_size,  # Keep for backward compatibility
            "s3_bucket": BUCKET_NAME,
            "s3_key": s3_video_key,
            "s3_video_key": s3_video_key,  # Keep for backward compatibility
            "processed_url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{s3_video_key}",
            "timestamp": timestamp,
            "upload_timestamp": timestamp,  # Keep for backward compatibility
            "runtime": 0,  # Will be updated by processor
            "status": "UPLOADED",
            "views": 0,
            "likes": 0,
            "engagement": 0
        }
        
        metadata_key = f"metadata/{file_id}.json"
        
        try:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json'
            )
            logger.info(f"Metadata stored in S3: s3://{BUCKET_NAME}/{metadata_key}")
        except ClientError as e:
            logger.error(f"S3 metadata upload failed for {file_id}: {str(e)}")
            # Video is already in S3, so we log but don't fail
        
        # Send SQS message for processing
        message = {
            "video_id": file_id,
            "s3_bucket": BUCKET_NAME,
            "s3_video_key": s3_video_key,
            "s3_metadata_key": metadata_key,
            "original_filename": file.filename
        }
        
        try:
            sqs_client.send_message(
                QueueUrl=QUEUE_URL,
                MessageBody=json.dumps(message)
            )
            logger.info(f"SQS message sent for processing: video_id={file_id}")
        except Exception as e:
            logger.error(f"Failed to send SQS message for {file_id}: {str(e)}")
            # Video and metadata are already stored, so we log but don't fail
        
        UPLOAD_COUNTER.inc()
        logger.info(f"Upload complete and job queued: video_id={file_id}, size={file_size} bytes")
        
        return {
            "status": "success",
            "video_id": file_id,
            "message": "Video uploaded to S3, metadata to S3, and processing started"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (like file size validation)
        raise
    except Exception as e:
        error_msg = f"Upload failed: {str(e)}"
        logger.error(f"Upload failed for {file.filename}: {error_msg}", exc_info=True)
        
        return {
            "status": "error",
            "detail": "Upload failed. Please try again."
        }

