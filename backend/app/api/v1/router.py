from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    dashboards,
    health,
    roles,
    superset,
    users,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(dashboards.router, prefix="/dashboards", tags=["Dashboards"])
api_router.include_router(superset.router, prefix="/superset", tags=["Superset Integration"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
