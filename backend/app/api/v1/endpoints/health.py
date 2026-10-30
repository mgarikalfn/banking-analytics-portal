from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter()


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Comprehensive health check for the portal backend and database connectivity."""
    db_healthy = False
    try:
        await db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception as e:
        db_healthy = False

    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": "Banking Analytics Portal API",
        "database": "connected" if db_healthy else "disconnected",
    }
