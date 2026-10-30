import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine, async_session_factory
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

INSECURE_PASSWORDS = {
    "admin",
    "password",
    "admin123",
    "password123",
    "adminbanking123!",
    "changethispassword123!",
    "changethis",
    "placeholder",
    "admin_password_placeholder",
    "changeme",
    "12345678",
    "qwerty1234",
    "secret",
}


def validate_initial_admin_credentials(email: Optional[str], password: Optional[str]) -> None:
    """Validate that initial administrator credentials are explicitly provided and secure."""
    if not email or not email.strip():
        raise ValueError(
            "FIRST_SUPERUSER_EMAIL is required for initial portal administrator setup."
        )
    if not password or len(password.strip()) < 8:
        raise ValueError(
            "FIRST_SUPERUSER_PASSWORD is required and must be at least 8 characters."
        )
    cleaned_pwd = password.strip().lower()
    if cleaned_pwd in INSECURE_PASSWORDS or "placeholder" in cleaned_pwd:
        raise ValueError(
            "FIRST_SUPERUSER_PASSWORD cannot be a known default or placeholder. "
            "Please configure a strong, unique administrator password in the environment."
        )


async def init_default_data() -> None:
    """Seed base roles, administrator, and dashboard metadata idempotently."""
    async with async_session_factory() as session:
        from sqlalchemy import select

        # 1. Seed standard banking roles idempotently
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
                logger.info(f"Seeded role: {role_name}")
            else:
                created_roles[role_name] = existing

        # 2. Seed initial administrator idempotently
        stmt = select(User).where(User.is_superuser == True)
        res = await session.execute(stmt)
        existing_superuser = res.scalars().first()

        if existing_superuser:
            logger.info(
                f"Superuser already exists ({existing_superuser.email}); "
                "preserving existing administrator credentials without modification."
            )
        else:
            # Require explicit, secure administrator credentials when initializing
            validate_initial_admin_credentials(
                settings.FIRST_SUPERUSER_EMAIL, settings.FIRST_SUPERUSER_PASSWORD
            )

            stmt = select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL.lower().strip())
            res = await session.execute(stmt)
            user_by_email = res.scalars().first()

            if user_by_email:
                logger.info(
                    f"User {user_by_email.email} already exists; preserving existing password."
                )
            else:
                admin_user = User(
                    email=settings.FIRST_SUPERUSER_EMAIL.lower().strip(),
                    hashed_password=hash_password(settings.FIRST_SUPERUSER_PASSWORD),
                    full_name=settings.FIRST_SUPERUSER_FULL_NAME,
                    is_active=True,
                    is_superuser=True,
                    roles=[created_roles["admin"]] if "admin" in created_roles else [],
                )
                session.add(admin_user)
                logger.info(f"Initialized new superuser: {admin_user.email}")

        # 3. Seed representative dashboard placeholders idempotently
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
                "requires_branch_scope": True,
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
    # NOTE: Schema management is strictly handled via Alembic migrations.
    # Base.metadata.create_all is intentionally removed.

    try:
        await init_default_data()
    except Exception as e:
        logger.critical(f"FATAL: Application initialization failed: {e}", exc_info=True)
        raise e

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
