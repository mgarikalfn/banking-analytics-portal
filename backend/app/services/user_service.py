from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PortalException, NotFoundError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.repositories.role_repo import RoleRepository
from app.schemas.user import UserCreate, UserUpdate, UserPasswordUpdate


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)

    async def create_user(self, user_in: UserCreate) -> User:
        existing = await self.user_repo.get_by_email(user_in.email)
        if existing:
            raise PortalException(status_code=400, detail="Email already registered")

        user = User(
            email=user_in.email.lower().strip(),
            hashed_password=hash_password(user_in.password),
            full_name=user_in.full_name.strip(),
            is_active=user_in.is_active,
            is_superuser=user_in.is_superuser,
            assigned_branch_id=user_in.assigned_branch_id,
        )

        if user_in.role_ids:
            roles = await self.role_repo.get_by_ids(user_in.role_ids)
            user.roles = roles

        return await self.user_repo.create(user)

    async def update_user(self, user_id: int, user_in: UserUpdate) -> User:
        user = await self.user_repo.get_with_roles(user_id)
        if not user:
            raise NotFoundError("User not found")

        update_dict = user_in.model_dump(exclude_unset=True, exclude={"role_ids"})
        for k, v in update_dict.items():
            setattr(user, k, v)

        if user_in.role_ids is not None:
            roles = await self.role_repo.get_by_ids(user_in.role_ids)
            user.roles = roles

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_password(
        self, user_id: int, pwd_in: UserPasswordUpdate
    ) -> None:
        user = await self.user_repo.get(user_id)
        if not user:
            raise NotFoundError("User not found")

        if not verify_password(pwd_in.current_password, user.hashed_password):
            raise PortalException(status_code=400, detail="Incorrect current password")

        user.hashed_password = hash_password(pwd_in.new_password)
        await self.session.flush()

    async def get_user_by_id(self, user_id: int) -> User:
        user = await self.user_repo.get_with_roles(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return await self.user_repo.get_all_with_roles(skip=skip, limit=limit)
