from typing import List, TYPE_CHECKING
from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.dashboard import Dashboard

# Association table for User <-> Role (Many to Many)
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

# Association table for Dashboard <-> Role (Many to Many permissions)
dashboard_roles = Table(
    "dashboard_roles",
    Base.metadata,
    Column("dashboard_id", Integer, ForeignKey("dashboards.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    users: Mapped[List["User"]] = relationship(
        "User", secondary=user_roles, back_populates="roles", lazy="selectin"
    )
    dashboards: Mapped[List["Dashboard"]] = relationship(
        "Dashboard", secondary=dashboard_roles, back_populates="allowed_roles", lazy="selectin"
    )
