"""User management and models."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User roles for authorization."""

    ADMIN = "admin"
    ANALYST = "analyst"
    DEVELOPER = "developer"
    TESTER = "tester"
    VIEWER = "viewer"


class UserPermission(str, Enum):
    """User permissions."""

    READ_QUERIES = "read:queries"
    WRITE_QUERIES = "write:queries"
    EXECUTE_TESTS = "execute:tests"
    MANAGE_USERS = "manage:users"
    MANAGE_SETTINGS = "manage:settings"
    VIEW_REPORTS = "view:reports"
    EXPORT_REPORTS = "export:reports"
    ADMIN_ACCESS = "admin:access"


# Permission mapping
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [p.value for p in UserPermission],
    UserRole.ANALYST: [
        UserPermission.READ_QUERIES.value,
        UserPermission.WRITE_QUERIES.value,
        UserPermission.VIEW_REPORTS.value,
        UserPermission.EXPORT_REPORTS.value,
    ],
    UserRole.DEVELOPER: [
        UserPermission.READ_QUERIES.value,
        UserPermission.WRITE_QUERIES.value,
        UserPermission.VIEW_REPORTS.value,
    ],
    UserRole.TESTER: [
        UserPermission.READ_QUERIES.value,
        UserPermission.WRITE_QUERIES.value,
        UserPermission.EXECUTE_TESTS.value,
        UserPermission.VIEW_REPORTS.value,
    ],
    UserRole.VIEWER: [
        UserPermission.READ_QUERIES.value,
        UserPermission.VIEW_REPORTS.value,
    ],
}


class User(BaseModel):
    """User model."""

    username: str
    email: Optional[EmailStr] = None
    hashed_password: str
    full_name: Optional[str] = None
    roles: list[UserRole] = [UserRole.VIEWER]
    permissions: list[UserPermission] = []
    is_active: bool = True
    created_at: datetime = None
    updated_at: datetime = None

    def __init__(self, **data):
        super().__init__(**data)
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
        # Set permissions based on roles
        if not self.permissions and self.roles:
            perms = set()
            for role in self.roles:
                perms.update(ROLE_PERMISSIONS.get(role, []))
            self.permissions = [UserPermission(p) for p in perms]


class UserCreate(BaseModel):
    """User creation request."""

    username: str
    email: Optional[EmailStr] = None
    password: str
    full_name: Optional[str] = None
    roles: list[UserRole] = [UserRole.VIEWER]


class UserUpdate(BaseModel):
    """User update request."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    roles: Optional[list[UserRole]] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """User response (no password)."""

    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    roles: list[UserRole] = []
    is_active: bool = True
    created_at: datetime = None
