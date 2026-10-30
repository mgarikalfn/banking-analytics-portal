import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import Base, engine, async_session_factory
from app.core.exceptions import PortalException
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.models.dashboard import Dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("banking_portal")


async def init_default_data() -> None:
    """Seed base roles, placeholder dashboards, and initial superuser if not present."""
    async with async_session_factory() as session:
        from sqlalchemy import select

        # Seed standard banking roles
        roles_data = [
            ("admin", "Full system administrator"),
            ("executive", "Executive leadership with portfolio overview"),
            ("branch_manager", "Branch manager with branch scope access"),
            ("compliance_officer", "Compliance & risk analytics"),
            ("financial_analyst", "Deep analytics & reporting"),
        ]
        created_roles = {}
        for role_name, desc in roles_data:
            stmt = select(Role).where(Role.name == role_name)
            res = await session.execute(stmt)
            existing = res.scalars().first()
            if not existing:
                r = Role(name=role_name, description=desc)
                session.add(r)
                await session.flush()
                created_roles[role_name] = r
            else:
                created_roles[role_name] = existing

        # Seed initial superuser
        stmt = select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL.lower())
        res = await session.execute(stmt)
        superuser = res.scalars().first()
        if not superuser:
            admin_user = User(
                email=settings.FIRST_SUPERUSER_EMAIL.lower(),
                hashed_password=hash_password(settings.FIRST_SUPERUSER_PASSWORD),
                full_name=settings.FIRST_SUPERUSER_FULL_NAME,
                is_active=True,
                is_superuser=True,
                roles=[created_roles["admin"]] if "admin" in created_roles else [],
            )
            session.add(admin_user)
            logger.info(f"Initialized superuser: {settings.FIRST_SUPERUSER_EMAIL}")

        # Seed representative dashboard placeholders (ready for Superset UUID mapping)
        dashboards_data = [
            {
                "slug": "executive-summary",
                "title": "Executive Banking Overview",
                "description": "High-level liquidity, deposit trends, and key performance indicators.",
                "category": "Executive",
                "superset_dashboard_id": "placeholder-uuid-executive-overview",
                "roles": ["admin", "executive"],
                "requires_branch_scope": False,
            },
            {
                "slug": "retail-deposits",
                "title": "Retail Deposits & Savings",
                "description": "Detailed deposit volume by product, customer segment, and retention rates.",
                "category": "Retail Banking",
                "superset_dashboard_id": "placeholder-uuid-retail-deposits",
                "roles": ["admin", "financial_analyst", "branch_manager"],
                "requires_branch_scope": False,
            },
            {
                "slug": "loan-portfolio-risk",
                "title": "Loan Portfolio & Credit Risk",
                "description": "Delinquency rates, NPL ratios, risk rating distributions, and stress metrics.",
                "category": "Risk & Compliance",
                "superset_dashboard_id": "placeholder-uuid-credit-risk",
                "roles": ["admin", "compliance_officer", "financial_analyst"],
                "requires_branch_scope": False,
            },
            {
                "slug": "branch-operations",
                "title": "Branch Operations & Teller Metrics",
                "description": "Transaction velocity, queue metrics, and branch performance indicators.",
                "category": "Operations",
                "superset_dashboard_id": "placeholder-uuid-branch-operations",
                "roles": ["admin", "branch_manager"],
                "requires_branch_scope": True,  # Architecture ready for branch RLS
            },
        ]

        for d_data in dashboards_data:
            stmt = select(Dashboard).where(Dashboard.slug == d_data["slug"])
            res = await session.execute(stmt)
            existing = res.scalars().first()
            if not existing:
                dash_roles = [created_roles[r] for r in d_data["roles"] if r in created_roles]
                dash = Dashboard(
                    slug=d_data["slug"],
                    title=d_data["title"],
                    description=d_data["description"],
                    category=d_data["category"],
                    superset_dashboard_id=d_data["superset_dashboard_id"],
                    allowed_roles=dash_roles,
                    requires_branch_scope=d_data["requires_branch_scope"],
                )
                session.add(dash)
                logger.info(f"Initialized dashboard metadata: {d_data['slug']}")

        await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifespan handler."""
    logger.info("Starting Banking Analytics Portal backend...")
    # Create tables if not present (in production Alembic is preferred)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default roles and admin
    try:
        await init_default_data()
    except Exception as e:
        logger.warning(f"Default data seeding notice: {e}")

    yield

    logger.info("Shutting down Banking Analytics Portal backend...")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Enterprise Banking Analytics Portal Backend with Secure Superset Embedded Analytics",
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS configuration allowing credentials (HTTP-only cookies)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(PortalException)
async def portal_exception_handler(request: Request, exc: PortalException) -> JSONResponse:
    """Consistent JSON response for portal-level exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error_code": exc.error_code,
            "data": exc.data,
        },
    )


# Mount API V1
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "status": "online",
        "api_docs": "/docs" if settings.DEBUG else "disabled",
    }
