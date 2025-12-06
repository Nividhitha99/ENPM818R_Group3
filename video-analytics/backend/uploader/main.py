from fastapi import FastAPI, UploadFile, File, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import boto3
import os
import uuid
import json
import time
import logging
from datetime import datetime
from prometheus_client import make_asgi_app, Counter, Histogram
from botocore.exceptions import ClientError, BotoCoreError

# Structured JSON Logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "uploader",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "video_id"):
            log_data["video_id"] = record.video_id
        if hasattr(record, "filename"):
            log_data["filename"] = record.filename
        if hasattr(record, "file_size"):
            log_data["file_size"] = record.file_size
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("uploader")
logger.setLevel(logging.INFO)
logger.handlers = [handler]
logger.propagate = False

# Silence uvicorn and botocore logs
logging.getLogger("uvicorn").handlers = []
logging.getLogger("uvicorn.access").handlers = []
logging.getLogger("botocore").setLevel(logging.CRITICAL)

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
UPLOAD_ERRORS = Counter('upload_api_errors_total', 'Total upload API errors', ['endpoint', 'status_code'])
FILE_SIZE_HISTOGRAM = Histogram('upload_file_size_bytes', 'Distribution of uploaded file sizes', buckets=[1e6, 10e6, 50e6, 100e6, 250e6, 500e6])

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

# Allowed video file extensions (case-insensitive)
ALLOWED_EXTENSIONS = {"mp4", "mov", "avi", "webm", "mkv", "flv", "wmv", "m4v"}
ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
    "video/x-matroska",
    "video/x-flv",
    "video/x-ms-wmv",
    "application/octet-stream"  # Some browsers send this for video files
}

# Helper functions
def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request headers or generate new one"""
    return request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

def validate_file_type(filename: str, content_type: str) -> tuple:
    """Validate file extension and content type"""
    if not filename:
        return False, "Filename is required"
    
    # Extract extension
    file_extension = filename.split(".")[-1].lower() if "." in filename else ""
    
    # Validate extension
    if file_extension not in ALLOWED_EXTENSIONS:
        return False, f"Invalid file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS)).upper()}"
    
    # Validate content type (optional, some browsers send generic types)
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        logger.warning(f"Unexpected content type: {content_type} for file {filename}")
    
    return True, ""

def log_with_context(level, message, correlation_id=None, video_id=None, filename=None, file_size=None):
    """Log with contextual information"""
    record = logging.LogRecord(
        name="uploader",
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    if correlation_id:
        record.correlation_id = correlation_id
    if video_id:
        record.video_id = video_id
    if filename:
        record.filename = filename
    if file_size is not None:
        record.file_size = file_size
    logger.handle(record)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_video(file: UploadFile = File(...), request: Request = None):
    """
    Upload video file to S3 and metadata to S3.
    Videos stored in S3, metadata stored as JSON in S3.
    Uses streaming upload (no memory buffering).
    Validates file type and size.
    """
    start_time = time.perf_counter()
    correlation_id = get_correlation_id(request) if request else str(uuid.uuid4())
    endpoint = "/upload"
    file_id = None
    s3_video_key = None
    
    try:
        # Validate file type
        is_valid, error_msg = validate_file_type(file.filename, file.content_type)
        if not is_valid:
            log_with_context(logging.WARNING, f"File type validation failed: {error_msg}", correlation_id, filename=file.filename)
            UPLOAD_ERRORS.labels(endpoint=endpoint, status_code=400).inc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        
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
            log_with_context(logging.WARNING, f"Could not determine file size: {str(e)}", correlation_id, filename=file.filename)
            file_size = 0
        
        # File size validation (500MB limit)
        if file_size > MAX_FILE_SIZE:
            log_with_context(logging.WARNING, f"File exceeds 500MB limit: {file_size} bytes", correlation_id, filename=file.filename, file_size=file_size)
            UPLOAD_ERRORS.labels(endpoint=endpoint, status_code=413).inc()
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Maximum file size is 500MB. File size: {file_size / (1024*1024):.2f}MB"
            )
        
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split(".")[-1].lower() if "." in file.filename else "mp4"
        s3_video_key = f"videos/{file_id}.{file_extension}"
        
        log_with_context(logging.INFO, "Upload started", correlation_id, file_id, file.filename, file_size)
        FILE_SIZE_HISTOGRAM.observe(file_size)
        
        # Store video file in S3 (streaming upload - no memory buffering)
        with UPLOAD_LATENCY.time():
            try:
                # Reset file pointer to beginning for streaming
                file.file.seek(0)
                s3_client.upload_fileobj(
                    file.file,  # File-like object that streams
                    BUCKET_NAME,
                    s3_video_key,
                    ExtraArgs={
                        "ContentType": file.content_type or "video/mp4"
                    }
                )
                log_with_context(logging.INFO, f"Video stored in S3: s3://{BUCKET_NAME}/{s3_video_key}", correlation_id, file_id, file.filename, file_size)
            except ClientError as e:
                log_with_context(logging.ERROR, f"S3 video upload failed: {str(e)}", correlation_id, file_id, file.filename)
                UPLOAD_ERRORS.labels(endpoint=endpoint, status_code=500).inc()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Upload failed. Please try again."
                )
            except BotoCoreError as e:
                log_with_context(logging.ERROR, f"BotoCore error during upload: {str(e)}", correlation_id, file_id, file.filename)
                UPLOAD_ERRORS.labels(endpoint=endpoint, status_code=500).inc()
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
            log_with_context(logging.INFO, f"Metadata stored in S3: s3://{BUCKET_NAME}/{metadata_key}", correlation_id, file_id)
        except ClientError as e:
            log_with_context(logging.ERROR, f"S3 metadata upload failed: {str(e)}", correlation_id, file_id)
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
            log_with_context(logging.INFO, "SQS message sent for processing", correlation_id, file_id)
        except Exception as e:
            log_with_context(logging.ERROR, f"Failed to send SQS message: {str(e)}", correlation_id, file_id)
            # Video and metadata are already stored, so we log but don't fail
        
        UPLOAD_COUNTER.inc()
        duration = time.perf_counter() - start_time
        log_with_context(logging.INFO, f"Upload complete: duration={duration:.2f}s", correlation_id, file_id, file.filename, file_size)
        
        return {
            "status": "success",
            "video_id": file_id,
            "message": "Video uploaded to S3, metadata to S3, and processing started"
        }
        
    except HTTPException as exc:
        # Re-raise HTTP exceptions (like file size validation)
        duration = time.perf_counter() - start_time
        UPLOAD_LATENCY.observe(duration)
        raise
    except Exception as e:
        duration = time.perf_counter() - start_time
        UPLOAD_LATENCY.observe(duration)
        UPLOAD_ERRORS.labels(endpoint=endpoint, status_code=500).inc()
        log_with_context(logging.ERROR, f"Unexpected error: {str(e)}", correlation_id, file_id, file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed. Please try again."
        )
    finally:
        # Always track latency
        duration = time.perf_counter() - start_time
        UPLOAD_LATENCY.observe(duration)

