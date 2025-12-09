-- Video Analytics PostgreSQL Schema
-- Run this after RDS is created

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
