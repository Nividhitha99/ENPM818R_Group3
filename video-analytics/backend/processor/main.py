from fastapi import FastAPI
import boto3
import os
import json
import time
import asyncio
import logging
import tempfile
import ffmpeg
import uuid
from datetime import datetime
from io import BytesIO
from PIL import Image
from prometheus_client import make_asgi_app, Counter, Histogram
from botocore.exceptions import ClientError, BotoCoreError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy import Column, String, BigInteger, Integer, TIMESTAMP, UUID as SQLA_UUID
from sqlalchemy.sql import func
from urllib.parse import quote

# ============================================================================
# STRUCTURED JSON LOGGING SETUP
# ============================================================================
class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON"""
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "processor",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        # Add extra fields if present (like correlation_id, video_id)
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "video_id"):
            log_data["video_id"] = record.video_id
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

# Configure logger with JSON formatter
logger = logging.getLogger("processor")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.handlers = [handler]
logger.propagate = False  # Don't propagate to root logger

# Disable uvicorn's default logging (so we only see our JSON logs)
logging.getLogger("uvicorn").handlers = []
logging.getLogger("uvicorn.access").handlers = []
logging.getLogger("botocore").setLevel(logging.CRITICAL)
logging.getLogger("botocore.credentials").setLevel(logging.CRITICAL)

app = FastAPI(title="Processor Service")

# ============================================================================
# PROMETHEUS METRICS
# ============================================================================
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

VIDEOS_PROCESSED = Counter('videos_processed_total', 'Total successfully processed videos')
VIDEOS_FAILED = Counter('videos_processing_errors_total', 'Total video processing errors')
PROCESSING_TIME = Histogram('video_processing_seconds', 'Time spent processing video')
SQS_MESSAGES_RECEIVED = Counter('sqs_messages_received_total', 'Total SQS messages received')
SQS_MESSAGES_DELETED = Counter('sqs_messages_deleted_total', 'Total SQS messages deleted')
SQS_ERRORS = Counter('sqs_errors_total', 'Total SQS errors')

# ============================================================================
# DATABASE SETUP
# ============================================================================
Base = declarative_base()


class Video(Base):
    __tablename__ = "videos"
    
    video_id = Column(SQLA_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    s3_bucket = Column(String(255), nullable=False)
    s3_key = Column(String(512), nullable=False)
    thumbnail_key = Column(String(512))
    size_bytes = Column(BigInteger)
    duration_seconds = Column(Integer)
    status = Column(String(50), default="UPLOADED")
    uploaded_at = Column(TIMESTAMP, server_default=func.now())
    processed_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


def get_rds_credentials():
    """Fetch RDS credentials from AWS Secrets Manager"""
    secret_name = os.getenv("RDS_SECRET_NAME", "video-analytics/rds-password")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region
    )
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        
        # If secret only contains 'password', build full credentials from environment
        if 'password' in secret and 'host' not in secret:
            return {
                'username': os.getenv('RDS_USERNAME', 'videoadmin'),
                'password': secret['password'],
                'host': os.getenv('RDS_HOST', 'video-analytics-db.cgn280g0e2jq.us-east-1.rds.amazonaws.com'),
                'port': os.getenv('RDS_PORT', '5432'),
                'dbname': os.getenv('RDS_DBNAME', 'video_analytics')
            }
        return secret
    except Exception as e:
        logger.error(f"Failed to fetch RDS credentials: {str(e)}")
        raise


def create_db_engine():
    """Create SQLAlchemy engine with connection pooling"""
    creds = get_rds_credentials()
    
    # URL-encode password to handle special characters
    encoded_password = quote(creds['password'], safe='')
    database_url = f"postgresql://{creds['username']}:{encoded_password}@{creds['host']}:{creds['port']}/{creds['dbname']}"
    
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False
    )
    
    return engine


def get_db_session():
    """Get a database session"""
    engine = create_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


# Initialize database
try:
    db_engine = create_db_engine()
    Base.metadata.create_all(bind=db_engine)
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")

# ============================================================================
# AWS CLIENTS & CONFIGURATION
# ============================================================================
endpoint_url = os.getenv("AWS_ENDPOINT_URL")  # None for real AWS, URL for LocalStack
sqs_client = boto3.client(
    'sqs',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=endpoint_url if endpoint_url else None
)
s3_client = boto3.client(
    's3',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=endpoint_url if endpoint_url else None
)

QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "video-analytics-uploads")
DLQ_URL = os.getenv("SQS_DLQ_URL", "")  # Dead-Letter Queue URL (optional)

# Retry configuration
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))  # Exponential backoff
PROCESSING_TIMEOUT = int(os.getenv("PROCESSING_TIMEOUT", "300"))  # 5 minutes

is_running = True

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def log_with_context(level, message, correlation_id=None, video_id=None, **kwargs):
    """Log with correlation_id and video_id context"""
    record = logging.LogRecord(
        name="processor",
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
    logger.handle(record)

def validate_video_id(video_id: str) -> bool:
    """Validate video_id format (should be UUID)"""
    if not video_id:
        return False
    try:
        uuid.UUID(video_id)
        return True
    except ValueError:
        # Allow non-UUID formats too (flexible)
        return len(video_id) > 5 and len(video_id) < 256

@app.get("/health")
def health_check():
    return {"status": "healthy", "worker_running": is_running}

async def process_message(message, correlation_id=None):
    """Process a single SQS message with error handling and retries"""
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
    
    retry_count = 0
    last_error = None
    
    while retry_count < MAX_RETRIES:
        try:
            # Parse message
            body = json.loads(message['Body'])
            video_id = body.get('video_id')
            
            # Validate video_id
            if not validate_video_id(video_id):
                log_with_context(logging.ERROR, 
                    f"Invalid video_id format: {video_id}", 
                    correlation_id=correlation_id, 
                    video_id=video_id)
                VIDEOS_FAILED.inc()
                return  # Don't retry invalid input
            
            log_with_context(logging.INFO, 
                f"Processing video (attempt {retry_count + 1}/{MAX_RETRIES})", 
                correlation_id=correlation_id, 
                video_id=video_id)
            
            s3_video_key = body.get('s3_video_key', f"videos/{video_id}.mp4")
            s3_metadata_key = body.get('s3_metadata_key', f"metadata/{video_id}.json")
            s3_bucket = body.get('s3_bucket', S3_BUCKET) or S3_BUCKET
            
            # Verify video exists in S3
            try:
                obj = s3_client.head_object(Bucket=s3_bucket, Key=s3_video_key)
                file_size = obj['ContentLength']
                log_with_context(logging.INFO, 
                    f"Video found in S3: s3://{s3_bucket}/{s3_video_key}, size={file_size} bytes", 
                    correlation_id=correlation_id, 
                    video_id=video_id)
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                log_with_context(logging.ERROR, 
                    f"Video not found in S3: {error_code}", 
                    correlation_id=correlation_id, 
                    video_id=video_id)
                VIDEOS_FAILED.inc()
                return  # Don't retry if video doesn't exist
            
            # Process video with timeout
            try:
                with PROCESSING_TIME.time():
                    await asyncio.wait_for(
                        process_video_async(video_id, s3_bucket, s3_video_key, s3_metadata_key, file_size, correlation_id),
                        timeout=PROCESSING_TIMEOUT
                    )
            except asyncio.TimeoutError:
                log_with_context(logging.ERROR, 
                    f"Processing timeout after {PROCESSING_TIMEOUT}s", 
                    correlation_id=correlation_id, 
                    video_id=video_id)
                last_error = "timeout"
                raise
            
            # Success
            VIDEOS_PROCESSED.inc()
            log_with_context(logging.INFO, 
                f"Successfully processed video", 
                correlation_id=correlation_id, 
                video_id=video_id)
            return
            
        except Exception as e:
            retry_count += 1
            last_error = str(e)
            log_with_context(logging.WARNING, 
                f"Processing error: {str(e)} (retry {retry_count}/{MAX_RETRIES})", 
                correlation_id=correlation_id, 
                video_id=video_id)
            
            if retry_count < MAX_RETRIES:
                # Exponential backoff
                wait_time = (RETRY_BACKOFF_FACTOR ** (retry_count - 1))
                log_with_context(logging.INFO, 
                    f"Waiting {wait_time}s before retry", 
                    correlation_id=correlation_id, 
                    video_id=video_id)
                await asyncio.sleep(wait_time)
            else:
                # All retries exhausted - send to DLQ
                log_with_context(logging.ERROR, 
                    f"All retries exhausted. Error: {last_error}", 
                    correlation_id=correlation_id, 
                    video_id=video_id)
                
                if DLQ_URL:
                    try:
                        sqs_client.send_message(
                            QueueUrl=DLQ_URL,
                            MessageBody=json.dumps({
                                "original_message": body,
                                "error": last_error,
                                "correlation_id": correlation_id,
                                "timestamp": int(time.time())
                            })
                        )
                        log_with_context(logging.INFO, 
                            f"Message sent to DLQ", 
                            correlation_id=correlation_id, 
                            video_id=video_id)
                    except Exception as dlq_error:
                        log_with_context(logging.ERROR, 
                            f"Failed to send to DLQ: {str(dlq_error)}", 
                            correlation_id=correlation_id, 
                            video_id=video_id)
                
                VIDEOS_FAILED.inc()
                return

async def process_video_async(video_id, s3_bucket, s3_video_key, s3_metadata_key, file_size, correlation_id):
    """Core video processing logic (extracted for timeout handling)"""
    # Simulated transcoding
    log_with_context(logging.INFO, 
        f"Starting simulated transcoding", 
        correlation_id=correlation_id, 
        video_id=video_id)
    await asyncio.sleep(3)  # Simulate processing
    
    # Generate runtime
    runtime_seconds = max(5, int(file_size / 50000))
    
    # Extract thumbnail
    thumbnail_url = ""
    thumbnail_key = f"thumbnails/{video_id}.jpg"
    
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
            temp_video_path = temp_video.name
            s3_client.download_file(s3_bucket, s3_video_key, temp_video_path)
        
        try:
            probe = ffmpeg.probe(temp_video_path)
            duration = float(probe['streams'][0].get('duration', 0))
            seek_time = min(1.0, duration / 2) if duration > 0 else 0.5
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_thumbnail:
                temp_thumbnail_path = temp_thumbnail.name
                
                ffmpeg.input(temp_video_path, ss=seek_time) \
                    .output(temp_thumbnail_path, vframes=1, vf='scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2') \
                    .overwrite_output() \
                    .run(quiet=True, capture_stderr=True)
                
                s3_client.upload_file(temp_thumbnail_path, s3_bucket, thumbnail_key, ExtraArgs={'ContentType': 'image/jpeg'})
                thumbnail_url = thumbnail_key
                os.unlink(temp_thumbnail_path)
                
        except Exception as e:
            log_with_context(logging.WARNING, 
                f"Thumbnail extraction failed: {str(e)}", 
                correlation_id=correlation_id, 
                video_id=video_id)
            size_mb = round(file_size / (1024 * 1024), 2)
            thumbnail_url = f"https://via.placeholder.com/320x180.png?text={size_mb}MB*{runtime_seconds}s"
        
        if os.path.exists(temp_video_path):
            os.unlink(temp_video_path)
            
    except Exception as e:
        log_with_context(logging.ERROR, 
            f"Thumbnail processing error: {str(e)}", 
            correlation_id=correlation_id, 
            video_id=video_id)
        size_mb = round(file_size / (1024 * 1024), 2)
        thumbnail_url = f"https://via.placeholder.com/320x180.png?text={size_mb}MB*{runtime_seconds}s"
    
    # Read existing metadata
    existing_metadata = {}
    try:
        metadata_response = s3_client.get_object(Bucket=s3_bucket, Key=s3_metadata_key)
        existing_metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
    except Exception:
        pass
    
    # Create metadata
    filename = s3_video_key.split("/")[-1] if "/" in s3_video_key else s3_video_key
    views = existing_metadata.get('views', 0)
    likes = existing_metadata.get('likes', 0)
    engagement = existing_metadata.get('engagement', 0)
    upload_timestamp = existing_metadata.get('upload_timestamp', existing_metadata.get('timestamp', int(time.time())))
    
    metadata = {
        "video_id": video_id,
        "filename": existing_metadata.get('filename', existing_metadata.get('original_filename', filename)),
        "s3_bucket": s3_bucket,
        "s3_key": s3_video_key,
        "s3_video_key": s3_video_key,
        "processed_url": f"https://{s3_bucket}.s3.amazonaws.com/{s3_video_key}",
        "thumbnail_url": thumbnail_url,
        "timestamp": upload_timestamp,
        "upload_timestamp": upload_timestamp,
        "size": file_size,
        "file_size": file_size,
        "runtime": runtime_seconds,
        "views": views,
        "likes": likes,
        "engagement": engagement,
        "status": "PROCESSED",
        "processed_timestamp": int(time.time()),
        "correlation_id": correlation_id
    }
    
    # Store in RDS database
    try:
        session = get_db_session()
        video = Video(
            video_id=uuid.UUID(video_id),
            filename=metadata.get('filename', filename),
            s3_bucket=s3_bucket,
            s3_key=s3_video_key,
            thumbnail_key=thumbnail_key if thumbnail_url and not thumbnail_url.startswith('https://via.placeholder') else None,
            size_bytes=file_size,
            duration_seconds=runtime_seconds,
            status="PROCESSED",
            processed_at=datetime.utcnow()
        )
        session.add(video)
        session.commit()
        session.close()
        log_with_context(logging.INFO, 
            f"Video metadata saved to RDS database", 
            correlation_id=correlation_id, 
            video_id=video_id)
    except Exception as e:
        log_with_context(logging.ERROR, 
            f"Failed to save video to RDS: {str(e)}", 
            correlation_id=correlation_id, 
            video_id=video_id)
    
    # Also store metadata in S3 for backward compatibility
    try:
        s3_client.put_object(
            Bucket=s3_bucket,
            Key=s3_metadata_key,
            Body=json.dumps(metadata, indent=2),
            ContentType="application/json"
        )
        log_with_context(logging.INFO, 
            f"Metadata updated in S3", 
            correlation_id=correlation_id, 
            video_id=video_id)
    except Exception as e:
        log_with_context(logging.ERROR, 
            f"Metadata storage failed: {str(e)}", 
            correlation_id=correlation_id, 
            video_id=video_id)
        raise

async def worker_loop():
    """Main worker loop that polls SQS and processes messages"""
    log_with_context(logging.INFO, "Worker loop started")
    
    while is_running:
        try:
            try:
                response = sqs_client.receive_message(
                    QueueUrl=QUEUE_URL,
                    MaxNumberOfMessages=5,  # Process up to 5 messages in parallel
                    WaitTimeSeconds=20,     # Long polling: wait up to 20 seconds
                    VisibilityTimeout=300   # 5 minutes: keep message invisible while processing
                )
                
                if 'Messages' in response:
                    SQS_MESSAGES_RECEIVED.inc(len(response['Messages']))
                    
                    # Process messages in parallel
                    tasks = []
                    for message in response['Messages']:
                        correlation_id = str(uuid.uuid4())
                        task = asyncio.create_task(process_message_safe(message, correlation_id))
                        tasks.append(task)
                    
                    # Wait for all messages to be processed
                    await asyncio.gather(*tasks, return_exceptions=True)
                else:
                    log_with_context(logging.DEBUG, "No messages received, waiting...")
                    await asyncio.sleep(1)
                    
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                log_with_context(logging.ERROR, f"SQS error: {error_code}")
                SQS_ERRORS.inc()
                await asyncio.sleep(5)  # Backoff on error
                
        except Exception as e:
            log_with_context(logging.ERROR, f"Worker loop error: {str(e)}")
            SQS_ERRORS.inc()
            await asyncio.sleep(5)

async def process_message_safe(message, correlation_id):
    """Wrapper to ensure message is deleted from SQS after processing"""
    try:
        await process_message(message, correlation_id)
    except Exception as e:
        log_with_context(logging.ERROR, f"Unhandled error in process_message: {str(e)}", correlation_id=correlation_id)
    finally:
        # Delete message from SQS (success or failure - don't want to reprocess)
        try:
            sqs_client.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )
            SQS_MESSAGES_DELETED.inc()
            log_with_context(logging.DEBUG, f"Message deleted from SQS", correlation_id=correlation_id)
        except Exception as e:
            log_with_context(logging.ERROR, f"Failed to delete SQS message: {str(e)}", correlation_id=correlation_id)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(worker_loop())

