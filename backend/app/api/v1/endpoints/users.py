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
from app.schemas.user import (
    UserCreate,
    UserPasswordUpdate,
    UserRead,
    UserUpdate,
)
from app.services.user_service import UserService

router = APIRouter()


@router.get("/", response_model=List[UserRead])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> List[UserRead]:
    """(Admin only) List all portal users."""
    service = UserService(db)
    users = await service.list_users(skip=skip, limit=limit)
    return [UserRead.model_validate(u) for u in users]


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf)],
)
async def create_user(
    user_in: UserCreate,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """(Admin only) Create a new portal user with assigned roles."""
    service = UserService(db)
    user = await service.create_user(user_in)
    return UserRead.model_validate(user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """Get details for a specific user."""
    # Allow user to get own info or require superuser
    if current_user.id != user_id and not current_user.is_superuser:
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError("Cannot view other user profiles")

    service = UserService(db)
    user = await service.get_user_by_id(user_id)
    return UserRead.model_validate(user)


@router.put(
    "/{user_id}",
    response_model=UserRead,
    dependencies=[Depends(verify_csrf)],
)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    _: User = Depends(get_current_active_superuser),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    """(Admin only) Update user attributes or assigned roles."""
    service = UserService(db)
    user = await service.update_user(user_id, user_in)
    return UserRead.model_validate(user)


@router.put(
    "/me/password",
    dependencies=[Depends(verify_csrf)],
)
async def update_current_user_password(
    pwd_in: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update current user's password using Argon2id."""
    service = UserService(db)
    await service.update_password(current_user.id, pwd_in)
    return {"message": "Password updated successfully"}
