from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.role import Role
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.email == email.lower().strip())
            .options(selectinload(User.roles))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_with_roles(self, user_id: int) -> Optional[User]:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_with_roles(self, skip: int = 0, limit: int = 100) -> List[User]:
        stmt = (
            select(User)
            .options(selectinload(User.roles))
            .order_by(User.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def assign_roles(self, user: User, roles: List[Role]) -> User:
        user.roles = roles
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user
