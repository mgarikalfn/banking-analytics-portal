from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.role import RoleRead


class DashboardBase(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9_-]+$")
    title: str = Field(..., min_length=2, max_length=200)
    description: str = Field(default="")
    category: str = Field(default="General", max_length=100)
    superset_dashboard_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="The Superset dashboard UUID or ID configured in Superset",
    )
    is_active: bool = True
    requires_branch_scope: bool = False


class DashboardCreate(DashboardBase):
    role_ids: List[int] = []


class DashboardUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    category: Optional[str] = None
    superset_dashboard_id: Optional[str] = None
    is_active: Optional[bool] = None
    requires_branch_scope: Optional[bool] = None
    role_ids: Optional[List[int]] = None


class DashboardRead(DashboardBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    allowed_roles: List[RoleRead] = []
    created_at: datetime
    updated_at: datetime


class DashboardCard(BaseModel):
    """Lightweight schema for dashboard catalog views."""
    id: int
    slug: str
    title: str
    description: str
    category: str
    is_active: bool
