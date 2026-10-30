from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.repositories.role_repo import RoleRepository
from app.schemas.role import RoleRead

router = APIRouter()


@router.get("/", response_model=List[RoleRead])
async def list_roles(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[RoleRead]:
    """List all available roles in the system."""
    role_repo = RoleRepository(db)
    roles = await role_repo.get_multi()
    return [RoleRead.model_validate(r) for r in roles]
