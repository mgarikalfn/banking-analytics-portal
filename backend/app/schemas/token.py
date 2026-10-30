from typing import List, Optional
from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: int
    type: str
    email: Optional[str] = None
    roles: List[str] = []
    is_superuser: bool = False


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    email: str
    password: str


class CSRFResponse(BaseModel):
    csrf_token: str
