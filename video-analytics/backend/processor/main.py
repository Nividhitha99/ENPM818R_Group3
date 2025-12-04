from fastapi import FastAPI
import boto3
import os
import json
import time
import asyncio
import logging
import tempfile
import ffmpeg
from io import BytesIO
from PIL import Image
from prometheus_client import make_asgi_app, Counter, Histogram
from botocore.exceptions import ClientError, BotoCoreError

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("processor")

app = FastAPI(title="Processor Service")

# Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

VIDEOS_PROCESSED = Counter('videos_processed_total', 'Total processed videos')
PROCESSING_TIME = Histogram('video_processing_seconds', 'Time spent processing video')

# AWS Clients - Real AWS (endpoint_url=None) or LocalStack (if AWS_ENDPOINT_URL is set)
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

is_running = True

@app.get("/health")
def health_check():
    return {"status": "healthy", "worker_running": is_running}

async def process_message(message):
    try:
        body = json.loads(message['Body'])
        video_id = body['video_id']
        s3_video_key = body.get('s3_video_key', f"videos/{video_id}.mp4")
        s3_metadata_key = body.get('s3_metadata_key', f"metadata/{video_id}.json")
        s3_bucket = body.get('s3_bucket', S3_BUCKET) or S3_BUCKET
        
        logger.info(f"Processing video {video_id}")
        
        # Verify video exists in S3 and extract file size
        try:
            obj = s3_client.head_object(Bucket=s3_bucket, Key=s3_video_key)
            file_size = obj['ContentLength']
            logger.info(f"Video found in S3: s3://{s3_bucket}/{s3_video_key}, size={file_size} bytes")
        except Exception as e:
            logger.error(f"Video not found in S3 for {video_id}: {str(e)}")
            return
        
        # ⭐ 1. Simulated Transcoding Step
        logger.info(f"Starting simulated transcoding for {video_id}")
        with PROCESSING_TIME.time():
            await asyncio.sleep(3)  # Simulate transcoding / heavy video processing
        
        # ⭐ 2. Extract Video File Size (already done above)
        # file_size is already extracted from head_object
        
        # ⭐ 3. Generate Fake Runtime
        runtime_seconds = max(5, int(file_size / 50000))  # Calculate runtime based on file size
        
        # ⭐ 4. Extract Real Thumbnail from Video
        thumbnail_url = ""
        thumbnail_key = f"thumbnails/{video_id}.jpg"
        
        try:
            # Download video from S3 to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_video:
                temp_video_path = temp_video.name
                s3_client.download_file(s3_bucket, s3_video_key, temp_video_path)
                logger.info(f"Downloaded video to temp file: {temp_video_path}")
            
            # Extract frame at 1 second (or middle if video is shorter)
            try:
                # Probe video to get duration
                probe = ffmpeg.probe(temp_video_path)
                duration = float(probe['streams'][0].get('duration', 0))
                seek_time = min(1.0, duration / 2) if duration > 0 else 0.5
                
                # Extract frame as image
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_thumbnail:
                    temp_thumbnail_path = temp_thumbnail.name
                    
                    # Use ffmpeg to extract frame
                    (
                        ffmpeg
                        .input(temp_video_path, ss=seek_time)
                        .output(temp_thumbnail_path, vframes=1, vf='scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2')
                        .overwrite_output()
                        .run(quiet=True, capture_stderr=True)
                    )
                    
                    logger.info(f"Extracted thumbnail frame at {seek_time}s: {temp_thumbnail_path}")
                    
                    # Upload thumbnail to S3
                    s3_client.upload_file(
                        temp_thumbnail_path,
                        s3_bucket,
                        thumbnail_key,
                        ExtraArgs={'ContentType': 'image/jpeg'}
                    )
                    
                    # Store thumbnail key in metadata (analytics will generate presigned URL)
                    thumbnail_url = thumbnail_key  # Store S3 key, not presigned URL (presigned URLs expire)
                    
                    logger.info(f"Uploaded thumbnail to S3: s3://{s3_bucket}/{thumbnail_key}")
                    
                    # Clean up temp files
                    os.unlink(temp_thumbnail_path)
                    
            except Exception as e:
                logger.warning(f"Failed to extract thumbnail from video {video_id}: {str(e)}")
                # Fallback to placeholder if extraction fails
                size_mb = round(file_size / (1024 * 1024), 2)
                thumbnail_text = f"{size_mb}MB*{runtime_seconds}s"
                thumbnail_url = f"https://via.placeholder.com/320x180.png?text={thumbnail_text}"
            
            # Clean up temp video file
            if os.path.exists(temp_video_path):
                os.unlink(temp_video_path)
                
        except Exception as e:
            logger.error(f"Error processing thumbnail for {video_id}: {str(e)}", exc_info=True)
            # Fallback to placeholder if all else fails
            size_mb = round(file_size / (1024 * 1024), 2)
            thumbnail_text = f"{size_mb}MB*{runtime_seconds}s"
            thumbnail_url = f"https://via.placeholder.com/320x180.png?text={thumbnail_text}"
        
        # Read existing metadata from S3 (if it exists) to preserve views/likes
        existing_metadata = {}
        try:
            metadata_response = s3_client.get_object(
                Bucket=s3_bucket,
                Key=s3_metadata_key
            )
            existing_metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
            logger.info(f"Retrieved existing metadata from S3: s3://{s3_bucket}/{s3_metadata_key}")
        except Exception as e:
            logger.info(f"No existing metadata found for {video_id}, creating new metadata")
        
        # ⭐ 5. Create Metadata JSON
        # Extract filename from s3_key
        filename = s3_video_key.split("/")[-1] if "/" in s3_video_key else s3_video_key
        
        # Preserve existing analytics data
        views = existing_metadata.get('views', 0)
        likes = existing_metadata.get('likes', 0)
        engagement = existing_metadata.get('engagement', 0)
        upload_timestamp = existing_metadata.get('upload_timestamp', existing_metadata.get('timestamp', int(time.time())))
        
        metadata = {
            "video_id": video_id,
            "filename": existing_metadata.get('filename', existing_metadata.get('original_filename', filename)),
            "s3_bucket": s3_bucket,
            "s3_key": s3_video_key,
            "s3_video_key": s3_video_key,  # Keep for backward compatibility
            "processed_url": f"https://{s3_bucket}.s3.amazonaws.com/{s3_video_key}",
            "thumbnail_url": thumbnail_url,
            "timestamp": upload_timestamp,
            "upload_timestamp": upload_timestamp,  # Keep for backward compatibility
            "size": file_size,
            "file_size": file_size,  # Keep for backward compatibility
            "runtime": runtime_seconds,
            "views": views,
            "likes": likes,
            "engagement": engagement,
            "status": "PROCESSED",
            "processed_timestamp": int(time.time())
        }
        
        # ⭐ 6. Store Metadata in S3
        try:
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=f"metadata/{video_id}.json",
                Body=json.dumps(metadata, indent=2),
                ContentType="application/json"
            )
            logger.info(f"Updated metadata in S3: video_id={video_id}, thumbnail_url={thumbnail_url}")
        except Exception as e:
            logger.error(f"Error updating metadata in S3 for {video_id}: {str(e)}")
            return
        
        # ⭐ 7. Delete SQS Message
        try:
            sqs_client.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )
            logger.info(f"Message deleted from SQS for video_id={video_id}")
        except Exception as e:
            logger.error(f"Failed to delete SQS message for video_id={video_id}: {str(e)}", exc_info=True)
            # Don't fail the entire processing if delete fails - message will become visible again after visibility timeout
        
        # ⭐ 8. Logging
        logger.info(f"Simulated transcoding complete for {video_id}")
        logger.info(f"Extracted metadata: size={file_size}, runtime={runtime_seconds}")
        logger.info(f"Generated thumbnail URL: {thumbnail_url}")
        
        VIDEOS_PROCESSED.inc()
        logger.info(f"Successfully processed {video_id} (video and metadata in S3)")
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)

async def worker_loop():
    logger.info("Starting worker loop")
    while is_running:
        try:
            response = sqs_client.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=5
            )
            
            if 'Messages' in response:
                for message in response['Messages']:
                    await process_message(message)
            else:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Worker loop error: {str(e)}")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(worker_loop())

