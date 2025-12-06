from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
import boto3
import os
import json
import logging
import uuid
import time
from datetime import datetime
from prometheus_client import make_asgi_app, Counter, Histogram
from typing import Optional
from botocore.exceptions import ClientError


# ============================================================================
# STRUCTURED JSON LOGGING
# ============================================================================
class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easier aggregation and search"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "analytics",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "video_id"):
            log_data["video_id"] = record.video_id
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)


logger = logging.getLogger("analytics")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.handlers = [handler]
logger.propagate = False

# Silence noisy third-party loggers (uvicorn/botocore)
logging.getLogger("uvicorn").handlers = []
logging.getLogger("uvicorn.access").handlers = []
logging.getLogger("botocore").setLevel(logging.CRITICAL)
logging.getLogger("botocore.credentials").setLevel(logging.CRITICAL)

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
LIKES_COUNTER = Counter('video_likes_total', 'Total video likes')
ENGAGEMENT_COUNTER = Counter('video_engagement_total', 'Total engagement increments')
API_ERRORS = Counter('analytics_api_errors_total', 'Total API errors', ['endpoint', 'status_code'])
API_LATENCY = Histogram(
    'analytics_api_latency_seconds',
    'API latency in seconds',
    ['endpoint', 'method']
)

# AWS Client - Real AWS (endpoint_url=None) or LocalStack (if AWS_ENDPOINT_URL is set)
endpoint_url = os.getenv("AWS_ENDPOINT_URL")  # None for real AWS, URL for LocalStack
s3_client = boto3.client(
    's3',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=endpoint_url if endpoint_url else None
)

S3_BUCKET = os.getenv("S3_BUCKET_NAME", "video-analytics-uploads")

# Presigned URL expiration time (1 hour)
PRESIGNED_URL_EXPIRATION = 3600


# ============================================================================
# HELPERS
# ============================================================================
def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from headers or generate a new one"""
    return request.headers.get("X-Correlation-ID") or str(uuid.uuid4())


def validate_video_id(video_id: str) -> bool:
    """Validate video_id format (UUID preferred, allow non-empty strings)"""
    if not video_id:
        return False
    try:
        uuid.UUID(video_id)
        return True
    except ValueError:
        # Allow non-UUID strings but non-empty
        return len(video_id.strip()) > 0


def log_with_context(level, message, correlation_id=None, video_id=None):
    record = logging.LogRecord(
        name="analytics",
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

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/videos")
def get_videos(
    request: Request,
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of videos to return"),
    sort_by: Optional[str] = Query("timestamp", description="Sort by: timestamp, views, likes, engagement")
):
    """Get list of all videos with their metadata."""
    start_time = time.perf_counter()
    correlation_id = get_correlation_id(request)
    endpoint = "/videos"
    method = "GET"
    try:
        videos = []
        try:
            response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix="metadata/",
                MaxKeys=limit * 2
            )

            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.json'):
                        try:
                            metadata_obj = s3_client.get_object(
                                Bucket=S3_BUCKET,
                                Key=obj['Key']
                            )
                            metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))

                            s3_key = metadata.get('s3_key', metadata.get('s3_video_key', ''))
                            # Generate presigned URL for video access with Content-Type for streaming
                            try:
                                content_type = metadata.get('content_type', 'video/mp4')
                                processed_url = s3_client.generate_presigned_url(
                                    'get_object',
                                    Params={
                                        'Bucket': S3_BUCKET,
                                        'Key': s3_key,
                                        'ResponseContentType': content_type
                                    },
                                    ExpiresIn=PRESIGNED_URL_EXPIRATION
                                )
                            except Exception as e:
                                log_with_context(logging.WARNING, f"Failed to generate presigned URL for {s3_key}: {str(e)}", correlation_id)
                                processed_url = metadata.get('processed_url', f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}")

                            thumbnail_url = metadata.get('thumbnail_url', '')

                            # If thumbnail_url is an S3 key (starts with thumbnails/), generate presigned URL
                            if thumbnail_url and thumbnail_url.startswith('thumbnails/'):
                                try:
                                    thumbnail_url = s3_client.generate_presigned_url(
                                        'get_object',
                                        Params={'Bucket': S3_BUCKET, 'Key': thumbnail_url},
                                        ExpiresIn=PRESIGNED_URL_EXPIRATION
                                    )
                                except Exception as e:
                                    log_with_context(logging.WARNING, f"Failed to generate presigned URL for thumbnail {thumbnail_url}: {str(e)}", correlation_id)
                                    # Keep original URL if presigned generation fails

                            if not thumbnail_url and metadata.get('status') == 'PROCESSED':
                                # Check if thumbnail exists in S3
                                thumbnail_key = f"thumbnails/{metadata.get('video_id')}.jpg"
                                try:
                                    s3_client.head_object(Bucket=S3_BUCKET, Key=thumbnail_key)
                                    thumbnail_url = s3_client.generate_presigned_url(
                                        'get_object',
                                        Params={'Bucket': S3_BUCKET, 'Key': thumbnail_key},
                                        ExpiresIn=PRESIGNED_URL_EXPIRATION
                                    )
                                    log_with_context(logging.INFO, f"Found thumbnail in S3 for {metadata.get('video_id')}, generated presigned URL", correlation_id, metadata.get('video_id'))
                                except ClientError:
                                    size_mb = round(metadata.get('size', metadata.get('file_size', 0)) / (1024 * 1024), 2)
                                    runtime = metadata.get('runtime', 0)
                                    if size_mb > 0 and runtime > 0:
                                        thumbnail_url = f"https://via.placeholder.com/320x180.png?text={size_mb}MB*{runtime}s"
                                        log_with_context(logging.INFO, f"Generated fallback thumbnail for {metadata.get('video_id')}: {thumbnail_url}", correlation_id, metadata.get('video_id'))

                            video = {
                                'video_id': metadata.get('video_id', ''),
                                'filename': metadata.get('filename', metadata.get('original_filename', 'unknown')),
                                's3_bucket': metadata.get('s3_bucket', S3_BUCKET),
                                's3_key': s3_key,
                                'processed_url': processed_url,
                                'thumbnail_url': thumbnail_url,
                                'timestamp': int(metadata.get('timestamp', metadata.get('upload_timestamp', 0))),
                                'size': int(metadata.get('size', metadata.get('file_size', 0))),
                                'runtime': int(metadata.get('runtime', 0)),
                                'views': int(metadata.get('views', 0)),
                                'likes': int(metadata.get('likes', 0)),
                                'status': metadata.get('status', 'UNKNOWN')
                            }
                            videos.append(video)
                        except Exception as e:
                            log_with_context(logging.WARNING, f"Error reading metadata file {obj['Key']}: {str(e)}", correlation_id)
                            continue
        except Exception as e:
            log_with_context(logging.ERROR, f"Error listing S3 objects: {str(e)}", correlation_id)
            raise HTTPException(status_code=500, detail=f"Failed to list videos: {str(e)}")

        if sort_by == 'views':
            videos.sort(key=lambda x: x['views'], reverse=True)
        elif sort_by == 'likes':
            videos.sort(key=lambda x: x['likes'], reverse=True)
        elif sort_by == 'engagement':
            videos.sort(key=lambda x: x.get('engagement', 0), reverse=True)
        else:
            videos.sort(key=lambda x: x['timestamp'], reverse=True)

        videos = videos[:limit]

        log_with_context(logging.INFO, f"[action=get_videos] Retrieved {len(videos)} videos", correlation_id)

        return {
            "count": len(videos),
            "videos": videos
        }
    except HTTPException as exc:
        API_ERRORS.labels(endpoint=endpoint, status_code=exc.status_code).inc()
        raise
    except Exception as e:
        API_ERRORS.labels(endpoint=endpoint, status_code=500).inc()
        log_with_context(logging.ERROR, f"[action=get_videos] Error getting videos: {str(e)}", correlation_id)
        raise HTTPException(status_code=500, detail=f"Failed to get videos: {str(e)}")
    finally:
        duration = time.perf_counter() - start_time
        API_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)

@app.get("/video/{video_id}")
def get_video(video_id: str, request: Request):
    """Get full metadata for a specific video."""
    start_time = time.perf_counter()
    correlation_id = get_correlation_id(request)
    endpoint = "/video/{video_id}"
    method = "GET"

    if not validate_video_id(video_id):
        API_ERRORS.labels(endpoint=endpoint, status_code=400).inc()
        raise HTTPException(status_code=400, detail="Invalid video_id format")

    try:
        metadata_key = f"metadata/{video_id}.json"

        try:
            metadata_obj = s3_client.get_object(
                Bucket=S3_BUCKET,
                Key=metadata_key
            )
            metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))

            s3_key = metadata.get('s3_key', metadata.get('s3_video_key', ''))
            try:
                content_type = metadata.get('content_type', 'video/mp4')
                processed_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': S3_BUCKET,
                        'Key': s3_key,
                        'ResponseContentType': content_type
                    },
                    ExpiresIn=PRESIGNED_URL_EXPIRATION
                )
            except Exception as e:
                log_with_context(logging.WARNING, f"Failed to generate presigned URL for {s3_key}: {str(e)}", correlation_id, video_id)
                processed_url = metadata.get('processed_url', f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}")

            thumbnail_url = metadata.get('thumbnail_url', '')

            if thumbnail_url and thumbnail_url.startswith('thumbnails/'):
                try:
                    thumbnail_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': S3_BUCKET, 'Key': thumbnail_url},
                        ExpiresIn=PRESIGNED_URL_EXPIRATION
                    )
                except Exception as e:
                    log_with_context(logging.WARNING, f"Failed to generate presigned URL for thumbnail {thumbnail_url}: {str(e)}", correlation_id, video_id)

            if not thumbnail_url and metadata.get('status') == 'PROCESSED':
                thumbnail_key = f"thumbnails/{video_id}.jpg"
                try:
                    s3_client.head_object(Bucket=S3_BUCKET, Key=thumbnail_key)
                    thumbnail_url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': S3_BUCKET, 'Key': thumbnail_key},
                        ExpiresIn=PRESIGNED_URL_EXPIRATION
                    )
                    log_with_context(logging.INFO, f"Found thumbnail in S3 for {video_id}, generated presigned URL", correlation_id, video_id)
                except ClientError:
                    size_mb = round(metadata.get('size', metadata.get('file_size', 0)) / (1024 * 1024), 2)
                    runtime = metadata.get('runtime', 0)
                    if size_mb > 0 and runtime > 0:
                        thumbnail_url = f"https://via.placeholder.com/320x180.png?text={size_mb}MB*{runtime}s"

            video = {
                'video_id': metadata.get('video_id', video_id),
                'filename': metadata.get('filename', metadata.get('original_filename', 'unknown')),
                's3_bucket': metadata.get('s3_bucket', S3_BUCKET),
                's3_key': s3_key,
                'processed_url': processed_url,
                'thumbnail_url': thumbnail_url,
                'timestamp': int(metadata.get('timestamp', metadata.get('upload_timestamp', 0))),
                'size': int(metadata.get('size', metadata.get('file_size', 0))),
                'runtime': int(metadata.get('runtime', 0)),
                'views': int(metadata.get('views', 0)),
                'likes': int(metadata.get('likes', 0)),
                'status': metadata.get('status', 'UNKNOWN'),
                'engagement': int(metadata.get('engagement', 0))
            }

            log_with_context(logging.INFO, f"[video_id={video_id}] [action=get_video] Retrieved video metadata", correlation_id, video_id)
            return video
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
            raise
    except HTTPException as exc:
        API_ERRORS.labels(endpoint=endpoint, status_code=exc.status_code).inc()
        raise
    except Exception as e:
        API_ERRORS.labels(endpoint=endpoint, status_code=500).inc()
        log_with_context(logging.ERROR, f"[video_id={video_id}] [action=get_video] Error getting video: {str(e)}", correlation_id, video_id)
        raise HTTPException(status_code=500, detail=f"Failed to get video: {str(e)}")
    finally:
        duration = time.perf_counter() - start_time
        API_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)

@app.get("/stats")
def get_stats(
    request: Request,
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    sort_by: Optional[str] = Query("timestamp", description="Sort by: timestamp, engagement, views, likes")
):
    start_time = time.perf_counter()
    correlation_id = get_correlation_id(request)
    endpoint = "/stats"
    method = "GET"

    try:
        processed_items = []
        try:
            response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix="metadata/",
                MaxKeys=limit * 2
            )

            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.json'):
                        try:
                            metadata_obj = s3_client.get_object(
                                Bucket=S3_BUCKET,
                                Key=obj['Key']
                            )
                            metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))

                            processed_item = {
                                'video_id': metadata.get('video_id', ''),
                                'status': metadata.get('status', 'UNKNOWN'),
                                'views': int(metadata.get('views', 0)),
                                'likes': int(metadata.get('likes', 0)),
                                'engagement': int(metadata.get('engagement', 0)),
                                'timestamp': int(metadata.get('upload_timestamp', metadata.get('timestamp', 0))),
                                's3_bucket': metadata.get('s3_bucket', S3_BUCKET),
                                's3_key': metadata.get('s3_video_key', ''),
                                'processed_url': f"https://{metadata.get('s3_bucket', S3_BUCKET)}.s3.amazonaws.com/{metadata.get('s3_video_key', '')}"
                            }
                            processed_items.append(processed_item)
                        except Exception as e:
                            log_with_context(logging.WARNING, f"Error reading metadata file {obj['Key']}: {str(e)}", correlation_id)
                            continue
        except Exception as e:
            log_with_context(logging.ERROR, f"Error listing S3 objects: {str(e)}", correlation_id)

        if sort_by == 'engagement':
            processed_items.sort(key=lambda x: x['engagement'], reverse=True)
        elif sort_by == 'views':
            processed_items.sort(key=lambda x: x['views'], reverse=True)
        elif sort_by == 'likes':
            processed_items.sort(key=lambda x: x['likes'], reverse=True)
        else:
            processed_items.sort(key=lambda x: x['timestamp'], reverse=True)

        processed_items = processed_items[:limit]

        log_with_context(logging.INFO, f"[action=get_stats] Retrieved stats: {len(processed_items)} items", correlation_id)

        return {
            "count": len(processed_items),
            "sort_by": sort_by,
            "items": processed_items
        }
    except Exception as e:
        API_ERRORS.labels(endpoint=endpoint, status_code=500).inc()
        log_with_context(logging.ERROR, f"[action=get_stats] Error getting stats: {str(e)}", correlation_id)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        duration = time.perf_counter() - start_time
        API_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)

@app.post("/view/{video_id}")
def record_view(video_id: str, request: Request):
    """Record a view for a video. Increments views and engagement."""
    start_time = time.perf_counter()
    correlation_id = get_correlation_id(request)
    endpoint = "/view/{video_id}"
    method = "POST"

    if not validate_video_id(video_id):
        API_ERRORS.labels(endpoint=endpoint, status_code=400).inc()
        raise HTTPException(status_code=400, detail="Invalid video_id format")

    try:
        metadata_key = f"metadata/{video_id}.json"

        try:
            metadata_obj = s3_client.get_object(
                Bucket=S3_BUCKET,
                Key=metadata_key
            )
            metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
            raise

        metadata['views'] = metadata.get('views', 0) + 1
        metadata['engagement'] = metadata.get('engagement', 0) + 1

        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=metadata_key,
            Body=json.dumps(metadata, indent=2),
            ContentType='application/json'
        )

        views = metadata['views']
        engagement = metadata['engagement']

        VIEWS_COUNTER.inc()
        ENGAGEMENT_COUNTER.inc()

        log_with_context(logging.INFO, f"[video_id={video_id}] [action=record_view] View recorded: views={views}, engagement={engagement}", correlation_id, video_id)

        return {
            "status": "view_recorded",
            "video_id": video_id,
            "views": views,
            "engagement": engagement
        }
    except HTTPException as exc:
        API_ERRORS.labels(endpoint=endpoint, status_code=exc.status_code).inc()
        raise
    except Exception as e:
        API_ERRORS.labels(endpoint=endpoint, status_code=500).inc()
        log_with_context(logging.ERROR, f"[video_id={video_id}] [action=record_view] Error recording view: {str(e)}", correlation_id, video_id)
        raise HTTPException(status_code=500, detail=f"Failed to record view: {str(e)}")
    finally:
        duration = time.perf_counter() - start_time
        API_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)


@app.post("/like/{video_id}")
def record_like(video_id: str, request: Request):
    """Record a like for a video. Increments likes and engagement."""
    start_time = time.perf_counter()
    correlation_id = get_correlation_id(request)
    endpoint = "/like/{video_id}"
    method = "POST"

    if not validate_video_id(video_id):
        API_ERRORS.labels(endpoint=endpoint, status_code=400).inc()
        raise HTTPException(status_code=400, detail="Invalid video_id format")

    try:
        metadata_key = f"metadata/{video_id}.json"

        try:
            metadata_obj = s3_client.get_object(
                Bucket=S3_BUCKET,
                Key=metadata_key
            )
            metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
            raise

        metadata['likes'] = metadata.get('likes', 0) + 1
        metadata['engagement'] = metadata.get('engagement', 0) + 1

        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=metadata_key,
            Body=json.dumps(metadata, indent=2),
            ContentType='application/json'
        )

        likes = metadata['likes']
        engagement = metadata['engagement']

        LIKES_COUNTER.inc()
        ENGAGEMENT_COUNTER.inc()

        log_with_context(logging.INFO, f"[video_id={video_id}] [action=record_like] Like recorded: likes={likes}, engagement={engagement}", correlation_id, video_id)

        return {
            "status": "like_recorded",
            "video_id": video_id,
            "likes": likes,
            "engagement": engagement
        }
    except HTTPException as exc:
        API_ERRORS.labels(endpoint=endpoint, status_code=exc.status_code).inc()
        raise
    except Exception as e:
        API_ERRORS.labels(endpoint=endpoint, status_code=500).inc()
        log_with_context(logging.ERROR, f"[video_id={video_id}] [action=record_like] Error recording like: {str(e)}", correlation_id, video_id)
        raise HTTPException(status_code=500, detail=f"Failed to record like: {str(e)}")
    finally:
        duration = time.perf_counter() - start_time
        API_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)

