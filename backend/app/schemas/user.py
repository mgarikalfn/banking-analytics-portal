from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.role import RoleRead


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    assigned_branch_id: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role_ids: List[int] = []


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    assigned_branch_id: Optional[str] = None
    role_ids: Optional[List[int]] = None


class UserPasswordUpdate(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    roles: List[RoleRead] = []
    created_at: datetime
    updated_at: datetime
