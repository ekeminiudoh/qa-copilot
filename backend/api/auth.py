"""Authentication and user management API endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user, get_current_user_db
from backend.db import get_db
from backend.db.crud import (
    authenticate_user,
    create_api_key,
    create_user,
    delete_user,
    get_user_by_username,
    list_api_keys,
    list_users,
    revoke_api_key,
    update_user,
)
from backend.db.models import UserDB
from backend.security import (
    TokenPair,
    create_access_token,
    create_refresh_token,
    decode_token,
    revoke_token,
)


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: Optional[EmailStr] = None
    password: str
    full_name: Optional[str] = None
    roles: List[str] = ["viewer"]


class RefreshRequest(BaseModel):
    refresh_token: str


class APIKeyCreateRequest(BaseModel):
    name: str
    expires_days: Optional[int] = None


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None


router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user: UserDB) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "roles": user.roles,
        "permissions": user.permissions,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/login", response_model=dict)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return access + refresh tokens."""
    user = await authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        username=user.username,
        roles=user.roles,
        permissions=user.permissions,
    )
    refresh_token = create_refresh_token(username=user.username)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": _user_response(user),
    }


@router.post("/refresh", response_model=dict)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    token_data = decode_token(request.refresh_token)
    if not token_data or token_data.token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await get_user_by_username(db, token_data.username)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Rotate: revoke old refresh token, issue new pair
    revoke_token(request.refresh_token)
    new_access = create_access_token(
        username=user.username, roles=user.roles, permissions=user.permissions
    )
    new_refresh = create_refresh_token(username=user.username)

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Revoke the current access token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        revoke_token(token)
    return {"message": "Logged out successfully"}


@router.post("/register", response_model=dict)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    existing = await get_user_by_username(db, request.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")

    from backend.models.user import ROLE_PERMISSIONS, UserRole
    perms: set = set()
    for role_str in request.roles:
        try:
            role = UserRole(role_str)
            perms.update(ROLE_PERMISSIONS.get(role, []))
        except ValueError:
            pass

    user = await create_user(
        db,
        username=request.username,
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        roles=request.roles,
        permissions=list(perms),
    )
    await db.commit()

    access_token = create_access_token(
        username=user.username, roles=user.roles, permissions=user.permissions
    )
    refresh_token = create_refresh_token(username=user.username)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": _user_response(user),
    }


@router.get("/me")
async def get_me(current_user: UserDB = Depends(get_current_user_db)):
    """Return the currently authenticated user's profile."""
    return _user_response(current_user)


@router.get("/users")
async def get_users(
    current_user: UserDB = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """List all users. Admin only."""
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    users = await list_users(db)
    return [_user_response(u) for u in users]


@router.put("/users/{username}")
async def update_user_endpoint(
    username: str,
    body: UserUpdateRequest,
    current_user: UserDB = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Update a user. Admin or self."""
    if "admin" not in current_user.roles and current_user.username != username:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    target = await get_user_by_username(db, username)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updates = body.model_dump(exclude_none=True)
    updated = await update_user(db, target.id, **updates)
    await db.commit()
    return _user_response(updated)


@router.delete("/users/{username}")
async def delete_user_endpoint(
    username: str,
    current_user: UserDB = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user. Admin only."""
    if "admin" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    target = await get_user_by_username(db, username)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await delete_user(db, target.id)
    await db.commit()
    return {"message": f"User '{username}' deleted"}


# ─── API Key Management ────────────────────────────────────────────────────────

@router.post("/api-keys")
async def create_key(
    body: APIKeyCreateRequest,
    current_user: UserDB = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new API key for the authenticated user."""
    from datetime import timedelta

    expires_at = None
    if body.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=body.expires_days)

    record, raw_key = await create_api_key(db, current_user.id, body.name, expires_at)
    await db.commit()
    return {
        "id": record.id,
        "name": record.name,
        "key": raw_key,  # shown only once
        "prefix": record.key_prefix,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
    }


@router.get("/api-keys")
async def get_api_keys(
    current_user: UserDB = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """List API keys for the authenticated user (without raw values)."""
    keys = await list_api_keys(db, current_user.id)
    return [
        {
            "id": k.id,
            "name": k.name,
            "prefix": k.key_prefix,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
        }
        for k in keys
    ]


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: UserDB = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key."""
    ok = await revoke_api_key(db, key_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    await db.commit()
    return {"message": "API key revoked"}
