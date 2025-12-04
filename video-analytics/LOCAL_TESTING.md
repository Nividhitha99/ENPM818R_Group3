# Local Testing Guide

## Overview
This guide explains how to run the video-analytics system locally without AWS credentials for development and testing purposes.

## Local Development Mode

The analytics and processor services support a **graceful degradation mode** when AWS credentials are unavailable. This allows you to:

- Develop and test locally without AWS access
- Use mock data for UI/frontend testing  
- Validate business logic without external dependencies
- Run the full Docker Compose stack on a local machine

## Starting Services

```bash
cd video-analytics
docker-compose up -d --build
```

All 6 services will start:
- **Frontend**: http://localhost:3000
- **Analytics API**: http://localhost:8002
- **Uploader API**: http://localhost:8001
- **Auth API**: http://localhost:8003
- **Gateway**: http://localhost:8000
- **Processor**: Internal service (no external port)

## Available Endpoints (Local/Mock Mode)

### Analytics Service (Port 8002)

**Health Check** - Verifies service and AWS availability:
```bash
curl http://localhost:8002/health
```

Response:
```json
{
  "status": "healthy",
  "service": "analytics",
  "aws_available": false
}
```

**Get All Videos** - Returns mock video data:
```bash
curl http://localhost:8002/videos
```

Response contains 3 mock videos with realistic engagement metrics:
- `video-001`: 1250 views, 87 likes
- `video-002`: 892 views, 56 likes
- `video-003`: 2100 views, 145 likes

**Get Individual Video**:
```bash
curl http://localhost:8002/video/video-001
```

**Record View**:
```bash
curl -X POST http://localhost:8002/view/video-001
```

**Record Like**:
```bash
curl -X POST http://localhost:8002/like/video-001
```

**Get Statistics**:
```bash
curl http://localhost:8002/stats
```

## Mock Data

When AWS credentials are unavailable (typical in local development), the following mock data is available:

### Video Objects Structure
Each mock video contains:
- `video_id`: Unique identifier (e.g., "video-001")
- `filename`: S3 filename
- `s3_bucket`: Mock bucket name
- `s3_key`: Mock S3 path
- `processed_url`: Placeholder image URL
- `thumbnail_url`: Placeholder thumbnail URL
- `timestamp`: Unix timestamp
- `size`: File size in bytes
- `runtime`: Video duration in seconds
- `views`: Current view count
- `likes`: Current like count
- `status`: Processing status ("PROCESSED")

### Mock Videos
```json
{
  "video_id": "video-001",
  "filename": "sample-video-1.mp4",
  "views": 1250,
  "likes": 87,
  "runtime": 300
}

{
  "video_id": "video-002",
  "filename": "sample-video-2.mp4",
  "views": 892,
  "likes": 56,
  "runtime": 480
}

{
  "video_id": "video-003",
  "filename": "sample-video-3.mp4",
  "views": 2100,
  "likes": 145,
  "runtime": 600
}
```

## Service Behavior Without AWS

### Analytics Service
- ✅ Returns mock video data
- ✅ Records view/like interactions in mock storage
- ✅ Serves all endpoints normally
- ⚠️ Does not sync to actual S3 buckets
- ⚠️ Data resets on service restart

### Processor Service
- ✅ Starts successfully and remains healthy
- ✅ Logs "Running in mock mode"
- ⚠️ Skips SQS queue polling (no job processing)
- ⚠️ Does not connect to S3 or perform video processing
- ℹ️ Suitable for testing gateway/auth layers

### Frontend Service
- ✅ Fully functional with mock data
- ✅ Can browse mock video list
- ✅ Can interact with analytics endpoints
- ⚠️ File upload may fail (uploader requires S3)

## Switching to AWS Mode

To enable full AWS integration:

1. **Set AWS credentials** in your environment:
   ```bash
   $env:AWS_ACCESS_KEY_ID = "your-key"
   $env:AWS_SECRET_ACCESS_KEY = "your-secret"
   $env:AWS_REGION = "us-east-1"
   ```

2. **Restart services**:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

3. **Verify AWS mode**:
   ```bash
   curl http://localhost:8002/health
   ```
   Response should show: `"aws_available": true`

## Troubleshooting

### Services showing "unhealthy" status

This is normal during startup. Wait 30 seconds for health checks to pass:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Port already in use

Stop conflicting services:
```bash
docker-compose down
```

### Need to rebuild after code changes

```bash
docker-compose up -d --build
```

### View service logs

```bash
# Analytics
docker logs video-analytics-analytics-1

# Processor
docker logs video-analytics-processor-1

# All services
docker-compose logs -f
```

## Testing Workflow

### 1. Verify All Services Running
```bash
docker ps  # All containers should show "Up"
```

### 2. Check Health Endpoints
```bash
curl http://localhost:8002/health
curl http://localhost:8001/health  # uploader (if available)
```

### 3. Test Data Retrieval
```bash
curl http://localhost:8002/videos | jq .
```

### 4. Test Interactions
```bash
curl -X POST http://localhost:8002/view/video-001
curl http://localhost:8002/stats | jq .
```

### 5. Frontend Testing
Open browser: http://localhost:3000
- Dashboard should load
- Video list should display 3 mock videos
- Analytics charts may show mock data or be empty (depends on frontend implementation)

## Architecture Notes

### Graceful Degradation Implementation

Both Analytics and Processor services implement a **try-except pattern** during startup:

```python
try:
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    sqs_client = boto3.client('sqs', region_name=AWS_REGION)
    AWS_AVAILABLE = True
except Exception as e:
    logger.warning(f"AWS initialization failed: {e}. Running in mock mode.")
    AWS_AVAILABLE = False
```

**Benefits:**
- ✅ Services don't crash without AWS credentials
- ✅ Development teams can work independently
- ✅ CI/CD pipelines can test without AWS
- ✅ Quick feedback loop for business logic changes

### Code Changes for Local Mode

See `backend/analytics/main.py` lines 30-219 and `backend/processor/main.py` lines 27-245 for implementation details.

## Next Steps

### Deploying to EKS with AWS

Once local testing validates your changes:

1. **Deploy K8s manifests** to EKS cluster
2. **Ensure IAM roles** are configured (see `iam/` directory)
3. **Configure environment variables** for AWS access
4. **Services will automatically enable AWS mode** when credentials available

See `MEMBER4-ARCHITECTURE.md` and `AWS_DEPLOYMENT_GUIDE.md` for production deployment details.

## Support

For questions about local testing setup:
- Check `backend/analytics/main.py` for analytics service implementation
- Check `backend/processor/main.py` for processor service implementation
- Review Docker logs: `docker-compose logs -f [service-name]`
- Verify port mappings: `docker ps --format "table {{.Names}}\t{{.Ports}}"`
