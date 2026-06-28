"""FastAPI dependencies for authentication and authorization."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.db.models import UserDB
from backend.security import decode_token

security = HTTPBearer(auto_error=False)


async def get_current_user_db(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserDB:
    """Resolve the current user from JWT Bearer token or API key.

    Supports two auth schemes:
    - Bearer <JWT access token>
    - Bearer <qac_... API key>
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials

    # Detect API key by prefix
    if token.startswith("qac_"):
        from backend.db.crud import get_api_key_by_raw, get_user_by_id
        from datetime import datetime

        key_record = await get_api_key_by_raw(db, token)
        if not key_record:
            raise credentials_exception

        # Update last_used_at (best-effort, non-blocking)
        key_record.last_used_at = datetime.utcnow()
        await db.flush()

        user = await get_user_by_id(db, key_record.user_id)
    else:
        # JWT path
        token_data = decode_token(token)
        if token_data is None or token_data.token_type != "access":
            raise credentials_exception

        from backend.db.crud import get_user_by_username
        user = await get_user_by_username(db, token_data.username)

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


# Backwards-compatible alias (used by existing endpoint code)
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> UserDB:
    return await get_current_user_db(credentials, db)


def require_permission(permission_value: str):
    """Dependency factory: require a specific permission string."""

    async def _check(current_user: UserDB = Depends(get_current_user_db)):
        if permission_value not in (current_user.permissions or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission_value}",
            )
        return current_user

    return _check


def require_role(role_value: str):
    """Dependency factory: require a specific role string."""

    async def _check(current_user: UserDB = Depends(get_current_user_db)):
        if role_value not in (current_user.roles or []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role_value}",
            )
        return current_user

    return _check


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db),
) -> Optional[UserDB]:
    """Returns the user if authenticated, None otherwise — for public endpoints."""
    if not credentials:
        return None
    try:
        return await get_current_user_db(credentials, db)
    except HTTPException:
        return None
