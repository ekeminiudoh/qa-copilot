"""User service for managing users."""

from typing import Dict, Optional

from backend.models.user import User, UserCreate, UserRole
from backend.security import get_password_hash


class UserService:
    """User management service."""

    def __init__(self):
        self.users: Dict[str, User] = {}
        self._init_default_users()

    def _init_default_users(self):
        """Initialize default admin and demo users."""
        from backend.config import settings
        
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin"),
            full_name="Administrator",
            roles=[UserRole.ADMIN],
            is_active=True,
        )
        self.users[admin_user.username] = admin_user

    def create_user(self, user_create: UserCreate) -> User:
        """Create a new user."""
        if user_create.username in self.users:
            raise ValueError(f"User {user_create.username} already exists")

        user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=get_password_hash(user_create.password),
            full_name=user_create.full_name,
            roles=user_create.roles,
        )
        self.users[user.username] = user
        return user

    def get_user(self, username: str) -> Optional[User]:
        """Get a user by username."""
        return self.users.get(username)

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email."""
        for user in self.users.values():
            if user.email == email:
                return user
        return None

    def list_users(self) -> list[User]:
        """List all users."""
        return list(self.users.values())

    def update_user(self, username: str, **kwargs) -> Optional[User]:
        """Update a user."""
        user = self.get_user(username)
        if not user:
            return None

        for key, value in kwargs.items():
            if key == "password":
                user.hashed_password = get_password_hash(value)
            elif hasattr(user, key):
                setattr(user, key, value)

        return user

    def delete_user(self, username: str) -> bool:
        """Delete a user."""
        if username in self.users:
            del self.users[username]
            return True
        return False

    def verify_user_credentials(self, username: str, password: str) -> Optional[User]:
        """Verify user credentials."""
        from backend.security import verify_password

        user = self.get_user(username)
        if not user or not user.is_active:
            return None
        if verify_password(password, user.hashed_password):
            return user
        return None


# Global user service instance
user_service = UserService()
