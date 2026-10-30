from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_superuser,
    get_current_user,
    get_db,
    verify_csrf,
)
from app.models.user import User
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardRead,
    DashboardUpdate,
)
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/", response_model=List[DashboardRead])
async def list_user_dashboards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DashboardRead]:
    """List all dashboards accessible to current user based on assigned roles."""
    service = DashboardService(db)
    dashboards = await service.list_for_user(
        user_id=current_user.id, is_superuser=current_user.is_superuser
    )
    return [DashboardRead.model_validate(d) for d in dashboards]


@router.get("/{dashboard_id}", response_model=DashboardRead)
async def get_dashboard(
    dashboard_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardRead:
    """Get metadata for a specific dashboard after verifying user role access."""
    service = DashboardService(db)
    dashboard = await service.check_access(
        user_id=current_user.id,
        dashboard_id=dashboard_id,
        is_superuser=current_user.is_superuser,
    )
    return DashboardRead.model_validate(dashboard)


@router.post(
    "/",
    response_model=DashboardRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_dashboard(
    dashboard_in: DashboardCreate,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> DashboardRead:
    """(Admin only) Register a new analytics dashboard."""
    service = DashboardService(db)
    dashboard = await service.create_dashboard(dashboard_in)
    return DashboardRead.model_validate(dashboard)


@router.put(
    "/{dashboard_id}",
    response_model=DashboardRead,
    dependencies=[Depends(verify_csrf)],
)
async def update_dashboard(
    dashboard_id: int,
    dashboard_in: DashboardUpdate,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> DashboardRead:
    """(Admin only) Update dashboard metadata and role assignments."""
    service = DashboardService(db)
    dashboard = await service.update_dashboard(dashboard_id, dashboard_in)
    return DashboardRead.model_validate(dashboard)
