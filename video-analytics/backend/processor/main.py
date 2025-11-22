from fastapi import FastAPI
import boto3
import os
import json
import time
import asyncio
import logging
from prometheus_client import make_asgi_app, Counter, Histogram

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("processor")

app = FastAPI(title="Processor Service")

# Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

VIDEOS_PROCESSED = Counter('videos_processed_total', 'Total processed videos')
PROCESSING_TIME = Histogram('video_processing_seconds', 'Time spent processing video')

# AWS Clients
sqs_client = boto3.client(
    'sqs',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=os.getenv("AWS_ENDPOINT_URL")
)
dynamodb = boto3.resource(
    'dynamodb',
    region_name=os.getenv("AWS_REGION", "us-east-1"),
    endpoint_url=os.getenv("AWS_ENDPOINT_URL")
)

QUEUE_URL = os.getenv("SQS_QUEUE_URL", "")
TABLE_NAME = os.getenv("DYNAMODB_TABLE_NAME", "video-metadata")

is_running = True

@app.get("/health")
def health_check():
    return {"status": "healthy", "worker_running": is_running}

async def process_message(message):
    try:
        body = json.loads(message['Body'])
        video_id = body['video_id']
        
        logger.info(f"Processing video {video_id}")
        
        # Simulate processing
        with PROCESSING_TIME.time():
            await asyncio.sleep(2) # Simulate transcoding
        
        # Update DynamoDB
        table = dynamodb.Table(TABLE_NAME)
        table.put_item(
            Item={
                'video_id': video_id,
                'status': 'PROCESSED',
                's3_bucket': body['s3_bucket'],
                's3_key': body['s3_key'],
                'processed_url': f"https://{body['s3_bucket']}.s3.amazonaws.com/{body['s3_key']}", # Mock URL
                'timestamp': int(time.time())
            }
        )
        
        # Delete message
        sqs_client.delete_message(
            QueueUrl=QUEUE_URL,
            ReceiptHandle=message['ReceiptHandle']
        )
        
        VIDEOS_PROCESSED.inc()
        logger.info(f"Successfully processed {video_id}")
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

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

