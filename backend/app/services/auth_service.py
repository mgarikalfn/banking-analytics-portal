from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_jwt_token,
    verify_password,
)
from app.core.exceptions import AuthenticationError
from app.models.user import User
from app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    async def authenticate(self, email: str, password: str) -> User:
        """Authenticate a user with email and password."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Incorrect email or password")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password")

        if not user.is_active:
            raise AuthenticationError("User account is inactive")

        return user

    def generate_tokens(self, user: User) -> Tuple[str, str]:
        """Generate access and refresh tokens for user."""
        roles = [r.name for r in user.roles]
        claims = {
            "email": user.email,
            "roles": roles,
            "is_superuser": user.is_superuser,
            "assigned_branch_id": user.assigned_branch_id,
        }
        access_token = create_access_token(subject=str(user.id), claims=claims)
        refresh_token = create_refresh_token(subject=str(user.id))
        return access_token, refresh_token

    async def refresh(self, refresh_token: str) -> Tuple[str, User]:
        """Validate refresh token and issue a fresh access token."""
        payload = decode_jwt_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise AuthenticationError("Invalid or expired refresh token")

        user_id = int(payload["sub"])
        user = await self.user_repo.get_with_roles(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        roles = [r.name for r in user.roles]
        claims = {
            "email": user.email,
            "roles": roles,
            "is_superuser": user.is_superuser,
            "assigned_branch_id": user.assigned_branch_id,
        }
        new_access_token = create_access_token(subject=str(user.id), claims=claims)
        return new_access_token, user
