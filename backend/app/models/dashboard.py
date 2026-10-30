from typing import List, TYPE_CHECKING
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.role import dashboard_roles

if TYPE_CHECKING:
    from app.models.role import Role


class Dashboard(Base, TimestampMixin):
    __tablename__ = "dashboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="General", nullable=False)

    # Apache Superset Dashboard ID (UUID or numeric ID in Superset)
    # Stored here as a documented placeholder until actual Superset dashboard is linked
    superset_dashboard_id: Mapped[str] = mapped_column(String(100), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Architecture hook: Ready for verified branch-level Row-Level Security once confirmed
    requires_branch_scope: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    allowed_roles: Mapped[List["Role"]] = relationship(
        "Role", secondary=dashboard_roles, back_populates="dashboards", lazy="selectin"
    )
