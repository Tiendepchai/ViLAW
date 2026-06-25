"""Optional JWT authentication middleware for ViLAW API."""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import jwt
import os
from datetime import datetime, timedelta, timezone

from shared.settings import settings

ALGORITHM = "HS256"


def create_token(user: str = "vilaw-user", expiry_hours: int = 24) -> str:
    payload = {
        "sub": user,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
    }
    return jwt.encode(payload, settings.auth_secret, algorithm=ALGORITHM)


async def auth_middleware(request: Request, call_next):
    """FastAPI middleware: checks Bearer token if AUTH_ENABLED=true."""
    if not settings.auth_enabled:
        return await call_next(request)

    # Public paths
    if request.url.path in ("/health", "/metrics", "/docs", "/openapi.json", "/v1/auth/login"):
        return await call_next(request)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Missing token", "code": 401})

    token = auth.split(" ", 1)[1]
    try:
        jwt.decode(token, settings.auth_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"error": "Token expired", "code": 401})
    except jwt.InvalidTokenError:
        return JSONResponse(status_code=401, content={"error": "Invalid token", "code": 401})

    return await call_next(request)
