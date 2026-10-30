from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError, PortalException
from app.models.dashboard import Dashboard
from app.repositories.dashboard_repo import DashboardRepository
from app.repositories.role_repo import RoleRepository
from app.schemas.dashboard import DashboardCreate, DashboardUpdate


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.dashboard_repo = DashboardRepository(session)
        self.role_repo = RoleRepository(session)

    async def list_for_user(
        self, user_id: int, is_superuser: bool = False
    ) -> List[Dashboard]:
        return await self.dashboard_repo.get_permitted_for_user(
            user_id, is_superuser=is_superuser
        )

    async def get_by_id(self, dashboard_id: int) -> Dashboard:
        dashboard = await self.dashboard_repo.get_with_roles(dashboard_id)
        if not dashboard:
            raise NotFoundError("Dashboard not found")
        return dashboard

    async def get_by_slug(self, slug: str) -> Dashboard:
        dashboard = await self.dashboard_repo.get_by_slug(slug)
        if not dashboard:
            raise NotFoundError("Dashboard not found")
        return dashboard

    async def check_access(
        self, user_id: int, dashboard_id: int, is_superuser: bool = False
    ) -> Dashboard:
        """Verify user has permission to access the dashboard."""
        dashboard = await self.get_by_id(dashboard_id)
        if not dashboard.is_active:
            raise PermissionDeniedError("Dashboard is currently inactive")

        if is_superuser:
            return dashboard

        has_access = await self.dashboard_repo.user_has_access(
            user_id=user_id, dashboard_id=dashboard_id, is_superuser=False
        )
        if not has_access:
            raise PermissionDeniedError(
                f"You do not have permission to view dashboard '{dashboard.title}'"
            )
        return dashboard

    async def create_dashboard(self, dash_in: DashboardCreate) -> Dashboard:
        existing = await self.dashboard_repo.get_by_slug(dash_in.slug)
        if existing:
            raise PortalException(
                status_code=400, detail="Dashboard with this slug already exists"
            )

        dashboard = Dashboard(
            slug=dash_in.slug.lower().strip(),
            title=dash_in.title.strip(),
            description=dash_in.description.strip(),
            category=dash_in.category.strip(),
            superset_dashboard_id=dash_in.superset_dashboard_id.strip(),
            is_active=dash_in.is_active,
            requires_branch_scope=dash_in.requires_branch_scope,
        )

        if dash_in.role_ids:
            roles = await self.role_repo.get_by_ids(dash_in.role_ids)
            dashboard.allowed_roles = roles

        return await self.dashboard_repo.create(dashboard)

    async def update_dashboard(
        self, dashboard_id: int, dash_in: DashboardUpdate
    ) -> Dashboard:
        dashboard = await self.get_by_id(dashboard_id)

        update_dict = dash_in.model_dump(exclude_unset=True, exclude={"role_ids"})
        for k, v in update_dict.items():
            setattr(dashboard, k, v)

        if dash_in.role_ids is not None:
            roles = await self.role_repo.get_by_ids(dash_in.role_ids)
            dashboard.allowed_roles = roles

        await self.session.flush()
        await self.session.refresh(dashboard)
        return dashboard

    async def list_all(
        self, skip: int = 0, limit: int = 100
    ) -> List[Dashboard]:
        return await self.dashboard_repo.get_all_with_roles(skip=skip, limit=limit)
