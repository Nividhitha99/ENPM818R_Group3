import json
import logging
import os
import uuid
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from prometheus_client import Counter, Histogram, make_asgi_app
from pydantic import BaseModel

app = FastAPI(title="Auth Service")

# Structured JSON Logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "service": "auth",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        if hasattr(record, "username"):
            log_data["username"] = record.username
        if hasattr(record, "roles"):
            log_data["roles"] = record.roles
        return json.dumps(log_data)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("auth")
logger.setLevel(logging.INFO)
logger.handlers = [handler]
logger.propagate = False

logging.getLogger("uvicorn").handlers = []
logging.getLogger("uvicorn.access").handlers = []
logging.getLogger("botocore").setLevel(logging.CRITICAL)


# AWS Secrets Manager integration
def get_secret_from_secrets_manager(secret_arn: str) -> str:
    """Fetch secret value from AWS Secrets Manager using IRSA"""
    try:
        session = boto3.session.Session()
        client = session.client(service_name='secretsmanager', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        response = client.get_secret_value(SecretId=secret_arn)
        return response['SecretString']
    except ClientError as e:
        logger.error(f"Failed to retrieve secret from Secrets Manager: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving secret: {e}")
        raise


# Configuration
if os.getenv("USE_SECRETS_MANAGER", "false").lower() == "true":
    JWT_SECRET_ARN = os.getenv("JWT_SECRET_ARN")
    if not JWT_SECRET_ARN:
        raise ValueError("JWT_SECRET_ARN environment variable is required when USE_SECRETS_MANAGER=true")
    logger.info("Fetching JWT_SECRET from AWS Secrets Manager")
    SECRET_KEY = get_secret_from_secrets_manager(JWT_SECRET_ARN)
    logger.info("Successfully retrieved JWT_SECRET from Secrets Manager")
else:
    SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey")
    logger.warning("Using JWT_SECRET from environment variable (not recommended for production)")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
DEFAULT_USERS = [
    {"username": "admin", "password": "password", "roles": ["admin", "user"]},
    {"username": "viewer", "password": "viewer", "roles": ["user"]},
]
USERS_ENV = os.getenv("AUTH_USERS_JSON")  # Optional JSON list of user objects


def load_users():
    try:
        if USERS_ENV:
            users = json.loads(USERS_ENV)
            if isinstance(users, list):
                return users
    except Exception as exc:  # pragma: no cover
        logger.error(f"Failed to parse AUTH_USERS_JSON: {exc}")
    return DEFAULT_USERS


users_data = load_users()
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Pre-hash user passwords
USER_DB = {
    u["username"]: {"username": u["username"], "password_hash": pwd_context.hash(u["password"]), "roles": u.get("roles", [])}
    for u in users_data
}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    roles: list[str]
    exp: int
    iat: int


# Metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

LOGIN_REQUESTS = Counter("auth_login_requests_total", "Total login requests")
LOGIN_SUCCESS = Counter("auth_login_success_total", "Successful logins")
LOGIN_FAILURE = Counter("auth_login_failure_total", "Failed logins")
VERIFY_REQUESTS = Counter("auth_verify_requests_total", "Token verification requests")
AUTH_ERRORS = Counter("auth_api_errors_total", "Auth API errors", ["endpoint", "status_code"])
AUTH_LATENCY = Histogram("auth_api_latency_seconds", "Auth API latency", ["endpoint", "method"], buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10))


# Helpers
def get_correlation_id(request: Request | None) -> str:
    if request and request.headers.get("X-Correlation-ID"):
        return request.headers.get("X-Correlation-ID")
    return str(uuid.uuid4())


def log_with_context(level, message, correlation_id=None, username=None, roles=None):
    record = logging.LogRecord(
        name="auth",
        level=level,
        pathname="",
        lineno=0,
        msg=message,
        args=(),
        exc_info=None,
    )
    if correlation_id:
        record.correlation_id = correlation_id
    if username:
        record.username = username
    if roles:
        record.roles = roles
    logger.handle(record)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def authenticate_user(username: str, password: str):
    user = USER_DB.get(username)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def create_access_token(username: str, roles: list[str], expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    now = datetime.utcnow()
    expire = now + timedelta(minutes=expires_minutes)
    to_encode = {
        "sub": username,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, int(expires_minutes * 60)


async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)):
    correlation_id = get_correlation_id(request)
    VERIFY_REQUESTS.inc()
    endpoint = "/verify"
    method = "GET"
    start = datetime.utcnow()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        roles: list[str] | None = payload.get("roles", [])
        if username is None:
            AUTH_ERRORS.labels(endpoint=endpoint, status_code=401).inc()
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username, "roles": roles, "correlation_id": correlation_id}
    except JWTError as exc:
        AUTH_ERRORS.labels(endpoint=endpoint, status_code=401).inc()
        log_with_context(logging.WARNING, f"Token verification failed: {exc}", correlation_id)
        raise HTTPException(status_code=401, detail="Invalid token")
    finally:
        duration = (datetime.utcnow() - start).total_seconds()
        AUTH_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)


def require_role(required_role: str):
    def role_checker(user=Depends(get_current_user)):
        roles = user.get("roles", [])
        if required_role not in roles:
            AUTH_ERRORS.labels(endpoint=f"require_role:{required_role}", status_code=403).inc()
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return role_checker


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/token", response_model=Token)
async def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    correlation_id = get_correlation_id(request)
    LOGIN_REQUESTS.inc()
    endpoint = "/token"
    method = "POST"
    start = datetime.utcnow()
    try:
        user = authenticate_user(form_data.username, form_data.password)
        if not user:
            LOGIN_FAILURE.inc()
            AUTH_ERRORS.labels(endpoint=endpoint, status_code=401).inc()
            log_with_context(logging.WARNING, "Invalid credentials", correlation_id, username=form_data.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token, expires_in = create_access_token(user["username"], user.get("roles", []))
        LOGIN_SUCCESS.inc()
        log_with_context(logging.INFO, "Login successful", correlation_id, username=user["username"], roles=user.get("roles", []))
        return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}
    finally:
        duration = (datetime.utcnow() - start).total_seconds()
        AUTH_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)


@app.get("/verify")
async def verify_token(user=Depends(get_current_user)):
    return {"username": user["username"], "roles": user.get("roles", []), "valid": True}


@app.get("/me")
async def read_users_me(user=Depends(get_current_user)):
    return {"username": user["username"], "roles": user.get("roles", [])}


@app.get("/admin/ping")
async def admin_ping(user=Depends(require_role("admin"))):
    return {"message": "pong", "user": user["username"], "roles": user.get("roles", [])}

