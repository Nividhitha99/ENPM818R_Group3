#!/usr/bin/env python3
"""Initialize RDS database schema from within pod"""

import boto3
import json
import logging
import os
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Get credentials from Secrets Manager
secret_name = os.getenv('RDS_SECRET_NAME', 'video-analytics/rds-password')
region = os.getenv('AWS_REGION', 'us-east-1')

try:
    client = boto3.client('secretsmanager', region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response['SecretString'])
    password = secret['password']
except Exception as e:
    logger.error(f'Failed to get credentials: {str(e)}')
    exit(1)

# Create connection string
db_url = f'postgresql://videoadmin:{password}@video-analytics-db.cgn280g0e2jq.us-east-1.rds.amazonaws.com:5432/video_analytics'
logger.info('Connecting to RDS database...')

try:
    engine = create_engine(db_url)
except Exception as e:
    logger.error(f'Failed to create engine: {str(e)}')
    exit(1)

# Schema SQL statements
schema_statements = [
    '''CREATE TABLE IF NOT EXISTS videos (
        video_id UUID PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        s3_bucket VARCHAR(255) NOT NULL,
        s3_key VARCHAR(512) NOT NULL,
        thumbnail_key VARCHAR(512),
        size_bytes BIGINT,
        duration_seconds INTEGER,
        status VARCHAR(50) DEFAULT 'UPLOADED',
        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''',
    '''CREATE TABLE IF NOT EXISTS video_views (
        id SERIAL PRIMARY KEY,
        video_id UUID REFERENCES videos(video_id) ON DELETE CASCADE,
        viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_ip VARCHAR(45),
        user_agent TEXT
    )''',
    '''CREATE TABLE IF NOT EXISTS video_likes (
        id SERIAL PRIMARY KEY,
        video_id UUID REFERENCES videos(video_id) ON DELETE CASCADE,
        liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_ip VARCHAR(45)
    )''',
    'CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status)',
    'CREATE INDEX IF NOT EXISTS idx_videos_uploaded_at ON videos(uploaded_at DESC)',
    'CREATE INDEX IF NOT EXISTS idx_views_video_id ON video_views(video_id)',
    'CREATE INDEX IF NOT EXISTS idx_views_viewed_at ON video_views(viewed_at DESC)',
    'CREATE INDEX IF NOT EXISTS idx_likes_video_id ON video_likes(video_id)',
    'CREATE INDEX IF NOT EXISTS idx_likes_liked_at ON video_likes(liked_at DESC)',
]

# Execute schema
try:
    logger.info('Executing schema initialization...')
    with engine.connect() as conn:
        for i, stmt in enumerate(schema_statements, 1):
            try:
                conn.execute(text(stmt))
                logger.info(f'✅ Statement {i}/{len(schema_statements)} executed')
            except Exception as e:
                error_msg = str(e)
                if 'already exists' in error_msg.lower():
                    logger.info(f'ℹ️  Statement {i}: Already exists (OK)')
                else:
                    logger.warning(f'⚠️  Statement {i}: {error_msg}')
        
        conn.commit()
        logger.info('✅ All schema statements executed!')
        
    # Verify schema
    logger.info('Verifying schema...')
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema='public' 
            AND table_name IN ('videos', 'video_views', 'video_likes')
        '''))
        table_count = result.scalar()
        logger.info(f'✅ Schema verification: {table_count} tables found')
        
        if table_count >= 3:
            logger.info('✅ Database schema initialization SUCCESSFUL!')
            exit(0)
        else:
            logger.error(f'❌ Expected 3 tables, found {table_count}')
            exit(1)
            
except Exception as e:
    logger.error(f'❌ Error: {str(e)}')
    import traceback
    traceback.print_exc()
    exit(1)
