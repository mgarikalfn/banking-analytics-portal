from app.repositories.base import BaseRepository
from app.repositories.user_repo import UserRepository
from app.repositories.role_repo import RoleRepository
from app.repositories.dashboard_repo import DashboardRepository
from app.repositories.audit_repo import AuditRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "RoleRepository",
    "DashboardRepository",
    "AuditRepository",
]
