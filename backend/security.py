"""JWT and authentication utilities."""

import secrets
from datetime import datetime, timedelta
from typing import Optional, Set

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from backend.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory token blacklist (move to Redis/DB in production)
_revoked_tokens: Set[str] = set()


class TokenData(BaseModel):
    """JWT token payload."""

    username: Optional[str] = None
    roles: list[str] = []
    permissions: list[str] = []
    token_type: str = "access"


class TokenPair(BaseModel):
    """Access + refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(
    username: str,
    roles: list[str] = None,
    permissions: list[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a short-lived JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.access_token_expire_minutes)

    expire = datetime.utcnow() + expires_delta
    payload = {
        "sub": username,
        "roles": roles or [],
        "permissions": permissions or [],
        "exp": expire,
        "type": "access",
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(username: str) -> str:
    """Create a long-lived JWT refresh token (7 days)."""
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {
        "sub": username,
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT token."""
    if token in _revoked_tokens:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        username: str = payload.get("sub")
        if username is None:
            return None
        return TokenData(
            username=username,
            roles=payload.get("roles", []),
            permissions=payload.get("permissions", []),
            token_type=payload.get("type", "access"),
        )
    except JWTError:
        return None


def revoke_token(token: str) -> None:
    """Add a token to the revocation list."""
    _revoked_tokens.add(token)


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return f"qac_{secrets.token_urlsafe(32)}"
