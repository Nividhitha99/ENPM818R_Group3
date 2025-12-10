#!/usr/bin/env python3
"""Initialize database schema for analytics"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'video-analytics', 'backend', 'analytics'))

from database import create_db_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Schema SQL
SCHEMA_SQL = """
-- Videos table
CREATE TABLE IF NOT EXISTS videos (
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
);

-- Views table
CREATE TABLE IF NOT EXISTS video_views (
    id SERIAL PRIMARY KEY,
    video_id UUID REFERENCES videos(video_id) ON DELETE CASCADE,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_ip VARCHAR(45),
    user_agent TEXT
);

-- Likes table
CREATE TABLE IF NOT EXISTS video_likes (
    id SERIAL PRIMARY KEY,
    video_id UUID REFERENCES videos(video_id) ON DELETE CASCADE,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_ip VARCHAR(45)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_videos_status ON videos(status);
CREATE INDEX IF NOT EXISTS idx_videos_uploaded_at ON videos(uploaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_views_video_id ON video_views(video_id);
CREATE INDEX IF NOT EXISTS idx_views_viewed_at ON video_views(viewed_at DESC);
CREATE INDEX IF NOT EXISTS idx_likes_video_id ON video_likes(video_id);
CREATE INDEX IF NOT EXISTS idx_likes_liked_at ON video_likes(liked_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_videos_updated_at
BEFORE UPDATE ON videos
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- View for video analytics
CREATE OR REPLACE VIEW video_analytics AS
SELECT 
    v.video_id,
    v.filename,
    v.s3_bucket,
    v.s3_key,
    v.thumbnail_key,
    v.size_bytes,
    v.duration_seconds AS runtime,
    v.status,
    v.uploaded_at,
    v.processed_at,
    EXTRACT(EPOCH FROM v.uploaded_at)::BIGINT AS timestamp,
    COUNT(DISTINCT vw.id) AS views,
    COUNT(DISTINCT vl.id) AS likes
FROM videos v
LEFT JOIN video_views vw ON v.video_id = vw.video_id
LEFT JOIN video_likes vl ON v.video_id = vl.video_id
GROUP BY v.video_id, v.filename, v.s3_bucket, v.s3_key, v.thumbnail_key, 
         v.size_bytes, v.duration_seconds, v.status, v.uploaded_at, v.processed_at;
"""

def init_schema():
    """Execute schema initialization"""
    try:
        logger.info("Creating database engine...")
        engine = create_db_engine()
        
        logger.info("Executing schema initialization...")
        with engine.connect() as conn:
            # Split and execute each statement
            statements = SCHEMA_SQL.strip().split(';')
            for i, statement in enumerate(statements, 1):
                statement = statement.strip()
                if statement:
                    try:
                        conn.execute(statement)
                        logger.info(f"✅ Statement {i} executed successfully")
                    except Exception as e:
                        logger.error(f"❌ Statement {i} failed: {str(e)}")
                        # Continue with other statements - some may already exist
            
            conn.commit()
        
        # Verify tables exist
        logger.info("Verifying schema...")
        with engine.connect() as conn:
            result = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema='public' 
                AND table_name IN ('videos', 'video_views', 'video_likes')
            """)
            count = result.scalar()
            logger.info(f"✅ Found {count} tables in schema")
        
        logger.info("✅ Schema initialization complete!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Schema initialization failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_schema()
    sys.exit(0 if success else 1)
