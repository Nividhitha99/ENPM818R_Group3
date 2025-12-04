from fastapi import FastAPI
import boto3
import os
import json
import time
import asyncio
import logging
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
        s3_bucket = body.get('s3_bucket', S3_BUCKET)
        
        logger.info(f"Processing video {video_id}")
        
        # Verify video exists in S3
        try:
            s3_client.head_object(Bucket=s3_bucket, Key=s3_video_key)
            logger.info(f"Video found in S3: s3://{s3_bucket}/{s3_video_key}")
        except Exception as e:
            logger.error(f"Video not found in S3 for {video_id}: {str(e)}")
            return
        
        # Simulate processing
        with PROCESSING_TIME.time():
            await asyncio.sleep(2)  # Simulate transcoding
        
        # Read metadata from S3
        try:
            metadata_response = s3_client.get_object(
                Bucket=s3_bucket,
                Key=s3_metadata_key
            )
            metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
            logger.info(f"Retrieved metadata from S3: s3://{s3_bucket}/{s3_metadata_key}")
        except Exception as e:
            logger.error(f"Error reading metadata from S3 for {video_id}: {str(e)}")
            metadata = {
                "video_id": video_id,
                "s3_bucket": s3_bucket,
                "s3_video_key": s3_video_key,
                "status": "PROCESSED",
                "processed_timestamp": int(time.time()),
                "views": 0,
                "likes": 0,
                "engagement": 0
            }
        
        # Update metadata in S3
        processed_timestamp = int(time.time())
        # Calculate runtime (simulated - in production, extract from video metadata)
        runtime = 2  # Simulated processing time in seconds
        
        metadata.update({
            'status': 'PROCESSED',
            'processed_timestamp': processed_timestamp,
            'processed_url': f"https://{s3_bucket}.s3.amazonaws.com/{s3_video_key}",
            'runtime': runtime,
            'views': metadata.get('views', 0),  # Preserve existing views
            'likes': metadata.get('likes', 0),  # Preserve existing likes
            'engagement': metadata.get('engagement', 0)  # Preserve existing engagement
        })
        
        # Ensure required fields exist
        if 'filename' not in metadata:
            metadata['filename'] = metadata.get('original_filename', f"video_{video_id}")
        if 's3_key' not in metadata:
            metadata['s3_key'] = s3_video_key
        if 'size' not in metadata:
            metadata['size'] = metadata.get('file_size', 0)
        if 'timestamp' not in metadata:
            metadata['timestamp'] = metadata.get('upload_timestamp', processed_timestamp)
        
        try:
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_metadata_key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json'
            )
            logger.info(f"Updated metadata in S3: video_id={video_id}")
        except Exception as e:
            logger.error(f"Error updating metadata in S3 for {video_id}: {str(e)}")
        
        # Delete message from SQS after successful processing
        try:
            sqs_client.delete_message(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=message['ReceiptHandle']
            )
            logger.info(f"Message deleted from SQS for video_id={video_id}")
        except Exception as e:
            logger.error(f"Failed to delete SQS message for video_id={video_id}: {str(e)}", exc_info=True)
            # Don't fail the entire processing if delete fails - message will become visible again after visibility timeout
        
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

