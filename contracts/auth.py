from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field


bearer_scheme = HTTPBearer(auto_error=False)


class TokenRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthenticatedUser(BaseModel):
    subject: str
    issuer: str
    scopes: list[str] = []


def create_access_token(subject: str, secret_key: str, issuer: str, expires_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iss": issuer,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
        "scopes": ["orders:read", "orders:write", "inventory:read", "inventory:write", "payments:read"],
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")


def verify_access_token(token: str, secret_key: str, issuer: str) -> AuthenticatedUser:
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"], issuer=issuer)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    scopes = payload.get("scopes", [])
    if not isinstance(scopes, list):
        scopes = []

    return AuthenticatedUser(subject=subject, issuer=issuer, scopes=[str(scope) for scope in scopes])


def build_auth_dependency(secret_key: str, issuer: str) -> Callable[[HTTPAuthorizationCredentials | None], AuthenticatedUser]:
    async def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> AuthenticatedUser:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

        return verify_access_token(credentials.credentials, secret_key, issuer)

    return require_user
