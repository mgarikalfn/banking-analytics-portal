from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dashboard import Dashboard
from app.models.role import Role, dashboard_roles, user_roles
from app.repositories.base import BaseRepository


class DashboardRepository(BaseRepository[Dashboard]):
    def __init__(self, session: AsyncSession):
        super().__init__(Dashboard, session)

    async def get_by_slug(self, slug: str) -> Optional[Dashboard]:
        stmt = (
            select(Dashboard)
            .where(Dashboard.slug == slug)
            .options(selectinload(Dashboard.allowed_roles))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_with_roles(self, dashboard_id: int) -> Optional[Dashboard]:
        stmt = (
            select(Dashboard)
            .where(Dashboard.id == dashboard_id)
            .options(selectinload(Dashboard.allowed_roles))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_with_roles(
        self, skip: int = 0, limit: int = 100
    ) -> List[Dashboard]:
        stmt = (
            select(Dashboard)
            .options(selectinload(Dashboard.allowed_roles))
            .order_by(Dashboard.id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_permitted_for_user(
        self, user_id: int, is_superuser: bool = False
    ) -> List[Dashboard]:
        """Fetch all active dashboards that a user has permissions to view."""
        if is_superuser:
            stmt = (
                select(Dashboard)
                .where(Dashboard.is_active == True)
                .options(selectinload(Dashboard.allowed_roles))
                .order_by(Dashboard.category, Dashboard.title)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())

        # For regular users, join through user_roles -> dashboard_roles
        stmt = (
            select(Dashboard)
            .join(dashboard_roles, Dashboard.id == dashboard_roles.c.dashboard_id)
            .join(user_roles, dashboard_roles.c.role_id == user_roles.c.role_id)
            .where(
                Dashboard.is_active == True,
                user_roles.c.user_id == user_id,
            )
            .options(selectinload(Dashboard.allowed_roles))
            .distinct()
            .order_by(Dashboard.category, Dashboard.title)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def user_has_access(
        self, user_id: int, dashboard_id: int, is_superuser: bool = False
    ) -> bool:
        """Check if user has access to a specific dashboard."""
        if is_superuser:
            dashboard = await self.get(dashboard_id)
            return dashboard is not None and dashboard.is_active

        stmt = (
            select(Dashboard.id)
            .join(dashboard_roles, Dashboard.id == dashboard_roles.c.dashboard_id)
            .join(user_roles, dashboard_roles.c.role_id == user_roles.c.role_id)
            .where(
                Dashboard.id == dashboard_id,
                Dashboard.is_active == True,
                user_roles.c.user_id == user_id,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar() is not None

    async def assign_roles(
        self, dashboard: Dashboard, roles: List[Role]
    ) -> Dashboard:
        dashboard.allowed_roles = roles
        self.session.add(dashboard)
        await self.session.flush()
        await self.session.refresh(dashboard)
        return dashboard
