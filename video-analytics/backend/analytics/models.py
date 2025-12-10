"""
SQLAlchemy models for video analytics
"""
from sqlalchemy import Column, String, BigInteger, Integer, TIMESTAMP, ForeignKey, UUID
from sqlalchemy.sql import func
from database import Base
import uuid


class Video(Base):
    __tablename__ = "videos"
    
    video_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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


class VideoView(Base):
    __tablename__ = "video_views"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.video_id", ondelete="CASCADE"), nullable=False)
    viewed_at = Column(TIMESTAMP, server_default=func.now())
    user_ip = Column(String(45))
    user_agent = Column(String)


class VideoLike(Base):
    __tablename__ = "video_likes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    video_id = Column(UUID(as_uuid=True), ForeignKey("videos.video_id", ondelete="CASCADE"), nullable=False)
    liked_at = Column(TIMESTAMP, server_default=func.now())
    user_ip = Column(String(45))
