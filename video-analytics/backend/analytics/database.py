"""
Database utility for connecting to RDS PostgreSQL
Handles Secrets Manager integration and connection pooling
"""
import os
import json
import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
import logging

logger = logging.getLogger("analytics")

Base = declarative_base()


def get_rds_credentials():
    """Fetch RDS credentials from AWS Secrets Manager"""
    secret_name = os.getenv("RDS_SECRET_NAME", "video-analytics/rds-password")
    region = os.getenv("AWS_REGION", "us-east-1")
    
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region
    )
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        
        # If secret only contains 'password', build full credentials from environment
        if 'password' in secret and 'host' not in secret:
            return {
                'username': os.getenv('RDS_USERNAME', 'videoadmin'),
                'password': secret['password'],
                'host': os.getenv('RDS_HOST', 'video-analytics-db.cgn280g0e2jq.us-east-1.rds.amazonaws.com'),
                'port': os.getenv('RDS_PORT', '5432'),
                'dbname': os.getenv('RDS_DBNAME', 'video_analytics')
            }
        return secret
    except Exception as e:
        logger.error(f"Failed to fetch RDS credentials: {str(e)}")
        raise


def create_db_engine():
    """Create SQLAlchemy engine with connection pooling"""
    creds = get_rds_credentials()
    
    database_url = f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['dbname']}"
    
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False
    )
    
    return engine


def get_db_session():
    """Get a database session"""
    engine = create_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def init_db():
    """Initialize database connection and test it"""
    try:
        engine = create_db_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("Database connection successful")
        return engine
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise
