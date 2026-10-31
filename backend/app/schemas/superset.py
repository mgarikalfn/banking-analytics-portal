from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SupersetRLSRule(BaseModel):
    """Row Level Security rule placeholder for Superset guest tokens."""
    clause: str
    dataset: Optional[int] = None


class SupersetGuestUser(BaseModel):
    username: str
    first_name: str = "Portal"
    last_name: str = "User"


class SupersetResource(BaseModel):
    type: str = "dashboard"
    id: str


class SupersetGuestTokenPayload(BaseModel):
    user: SupersetGuestUser
    resources: List[SupersetResource]
    rls: List[Dict[str, Any]] = []


class SupersetGuestTokenRequest(BaseModel):
    dashboard_id: int = Field(..., description="Internal banking portal dashboard ID")


class SupersetGuestTokenResponse(BaseModel):
    token: str = Field(..., description="Signed Superset guest token")
    superset_dashboard_id: str = Field(..., description="Superset native dashboard UUID/ID to embed")
    superset_domain: str = Field(
        ..., description="Browser-facing Superset URL for the Embedded SDK"
    )
    expires_in: int = Field(..., description="Token lifespan in seconds")
    dashboard_title: str
    requires_branch_scope: bool = False


class SupersetHealthResponse(BaseModel):
    configured: bool
    superset_url: str
    connected: bool
    status_detail: str
