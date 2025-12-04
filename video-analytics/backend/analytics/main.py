from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import boto3
import os
import json
import logging
from prometheus_client import make_asgi_app, Counter
from typing import Optional
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
LIKES_COUNTER = Counter('video_likes_total', 'Total video likes')
ENGAGEMENT_COUNTER = Counter('video_engagement_total', 'Total engagement increments')

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

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/videos")
def get_videos(
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of videos to return"),
    sort_by: Optional[str] = Query("timestamp", description="Sort by: timestamp, views, likes, engagement")
):
    """
    Get list of all videos with their metadata.
    """
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
                            # Generate presigned URL for video access
                            try:
                                processed_url = s3_client.generate_presigned_url(
                                    'get_object',
                                    Params={'Bucket': S3_BUCKET, 'Key': s3_key},
                                    ExpiresIn=PRESIGNED_URL_EXPIRATION
                                )
                            except Exception as e:
                                logger.warning(f"Failed to generate presigned URL for {s3_key}: {str(e)}")
                                processed_url = metadata.get('processed_url', f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}")
                            
                            video = {
                                'video_id': metadata.get('video_id', ''),
                                'filename': metadata.get('filename', metadata.get('original_filename', 'unknown')),
                                's3_bucket': metadata.get('s3_bucket', S3_BUCKET),
                                's3_key': s3_key,
                                'processed_url': processed_url,
                                'timestamp': int(metadata.get('timestamp', metadata.get('upload_timestamp', 0))),
                                'size': int(metadata.get('size', metadata.get('file_size', 0))),
                                'runtime': int(metadata.get('runtime', 0)),
                                'views': int(metadata.get('views', 0)),
                                'likes': int(metadata.get('likes', 0)),
                                'status': metadata.get('status', 'UNKNOWN')
                            }
                            videos.append(video)
                        except Exception as e:
                            logger.warning(f"Error reading metadata file {obj['Key']}: {str(e)}")
                            continue
        except Exception as e:
            logger.error(f"Error listing S3 objects: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to list videos: {str(e)}")
        
        # Sort videos
        if sort_by == 'views':
            videos.sort(key=lambda x: x['views'], reverse=True)
        elif sort_by == 'likes':
            videos.sort(key=lambda x: x['likes'], reverse=True)
        elif sort_by == 'engagement':
            videos.sort(key=lambda x: x.get('engagement', 0), reverse=True)
        else:  # timestamp (default)
            videos.sort(key=lambda x: x['timestamp'], reverse=True)
        
        videos = videos[:limit]
        
        logger.info(f"[action=get_videos] Retrieved {len(videos)} videos")
        
        return {
            "count": len(videos),
            "videos": videos
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[action=get_videos] Error getting videos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get videos: {str(e)}")

@app.get("/video/{video_id}")
def get_video(video_id: str):
    """
    Get full metadata for a specific video.
    """
    try:
        metadata_key = f"metadata/{video_id}.json"
        
        try:
            metadata_obj = s3_client.get_object(
                Bucket=S3_BUCKET,
                Key=metadata_key
            )
            metadata = json.loads(metadata_obj['Body'].read().decode('utf-8'))
            
            # Format response with all required fields
            s3_key = metadata.get('s3_key', metadata.get('s3_video_key', ''))
            # Generate presigned URL for video access
            try:
                processed_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': S3_BUCKET, 'Key': s3_key},
                    ExpiresIn=PRESIGNED_URL_EXPIRATION
                )
            except Exception as e:
                logger.warning(f"Failed to generate presigned URL for {s3_key}: {str(e)}")
                processed_url = metadata.get('processed_url', f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}")
            
            video = {
                'video_id': metadata.get('video_id', video_id),
                'filename': metadata.get('filename', metadata.get('original_filename', 'unknown')),
                's3_bucket': metadata.get('s3_bucket', S3_BUCKET),
                's3_key': s3_key,
                'processed_url': processed_url,
                'timestamp': int(metadata.get('timestamp', metadata.get('upload_timestamp', 0))),
                'size': int(metadata.get('size', metadata.get('file_size', 0))),
                'runtime': int(metadata.get('runtime', 0)),
                'views': int(metadata.get('views', 0)),
                'likes': int(metadata.get('likes', 0)),
                'status': metadata.get('status', 'UNKNOWN'),
                'engagement': int(metadata.get('engagement', 0))
            }
            
            logger.info(f"[video_id={video_id}] [action=get_video] Retrieved video metadata")
            return video
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
            raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[video_id={video_id}] [action=get_video] Error getting video: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get video: {str(e)}")

@app.get("/stats")
def get_stats(
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    sort_by: Optional[str] = Query("timestamp", description="Sort by: timestamp, engagement, views, likes")
):
    try:
        # List all metadata files from S3
        processed_items = []
        try:
            response = s3_client.list_objects_v2(
                Bucket=S3_BUCKET,
                Prefix="metadata/",
                MaxKeys=limit * 2  # Get more to account for filtering
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.json'):
                        try:
                            # Get metadata file
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
                            logger.warning(f"Error reading metadata file {obj['Key']}: {str(e)}")
                            continue
        except Exception as e:
            logger.error(f"Error listing S3 objects: {str(e)}")
        
        # Sort items
        if sort_by == 'engagement':
            processed_items.sort(key=lambda x: x['engagement'], reverse=True)
        elif sort_by == 'views':
            processed_items.sort(key=lambda x: x['views'], reverse=True)
        elif sort_by == 'likes':
            processed_items.sort(key=lambda x: x['likes'], reverse=True)
        else:  # timestamp (default)
            processed_items.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Limit results
        processed_items = processed_items[:limit]
        
        logger.info(f"[action=get_stats] Retrieved stats: {len(processed_items)} items")
        
        return {
            "count": len(processed_items),
            "sort_by": sort_by,
            "items": processed_items
        }
    except Exception as e:
        logger.error(f"[action=get_stats] Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/view/{video_id}")
def record_view(video_id: str):
    """
    Record a view for a video. Increments views and engagement in S3 metadata.
    """
    try:
        metadata_key = f"metadata/{video_id}.json"
        
        # Read current metadata
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
        
        # Increment views and engagement
        metadata['views'] = metadata.get('views', 0) + 1
        metadata['engagement'] = metadata.get('engagement', 0) + 1
        
        # Update metadata in S3
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
        
        logger.info(f"[video_id={video_id}] [action=record_view] View recorded: views={views}, engagement={engagement}")
        
        return {
            "status": "view_recorded",
            "video_id": video_id,
            "views": views,
            "engagement": engagement
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[video_id={video_id}] [action=record_view] Error recording view: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to record view: {str(e)}")


@app.post("/like/{video_id}")
def record_like(video_id: str):
    """
    Record a like for a video. Increments likes and engagement in S3 metadata.
    """
    try:
        metadata_key = f"metadata/{video_id}.json"
        
        # Read current metadata
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
        
        # Increment likes and engagement
        metadata['likes'] = metadata.get('likes', 0) + 1
        metadata['engagement'] = metadata.get('engagement', 0) + 1
        
        # Update metadata in S3
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
        
        logger.info(f"[video_id={video_id}] [action=record_like] Like recorded: likes={likes}, engagement={engagement}")
        
        return {
            "status": "like_recorded",
            "video_id": video_id,
            "likes": likes,
            "engagement": engagement
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[video_id={video_id}] [action=record_like] Error recording like: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to record like: {str(e)}")

