from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.repositories.audit_repo import AuditRepository


class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def log(
        self,
        *,
        user_id: Optional[int],
        action: str,
        resource: str,
        details: str = "",
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        return await self.audit_repo.create_log(
            user_id=user_id,
            action=action,
            resource=resource,
            details=details,
            ip_address=ip_address,
        )

    async def get_recent(self, limit: int = 50) -> List[AuditLog]:
        return await self.audit_repo.get_recent(limit=limit)
