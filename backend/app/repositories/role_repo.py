from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    def __init__(self, session: AsyncSession):
        super().__init__(Role, session)

    async def get_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name.strip().lower())
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_ids(self, ids: List[int]) -> List[Role]:
        if not ids:
            return []
        stmt = select(Role).where(Role.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
