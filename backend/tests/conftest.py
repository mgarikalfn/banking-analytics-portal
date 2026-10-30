import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Configure valid 32+ character keys for automated test suite execution
if not settings.SECRET_KEY or "insecure" in settings.SECRET_KEY.lower():
    settings.SECRET_KEY = "a1b2c3d4e5f678901234567890abcdefa1b2c3d4e5f678901234567890abcdef"
if not settings.CSRF_SECRET_KEY or "insecure" in settings.CSRF_SECRET_KEY.lower():
    settings.CSRF_SECRET_KEY = "fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321"

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.dashboard import Dashboard
from app.models.role import Role
from app.models.user import User

# Test in-memory SQLite database
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def seed_data(db_session: AsyncSession):
    """Seed test roles, users, and dashboards."""
    # Roles
    admin_role = Role(name="admin", description="Administrator")
    manager_role = Role(name="branch_manager", description="Branch Manager")
    analyst_role = Role(name="financial_analyst", description="Analyst")
    db_session.add_all([admin_role, manager_role, analyst_role])
    await db_session.flush()

    # Users
    admin_user = User(
        email="admin@bank.internal",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
        roles=[admin_role],
    )
    manager_user = User(
        email="manager@bank.internal",
        hashed_password=hash_password("ManagerPass123!"),
        full_name="Manager User",
        is_active=True,
        is_superuser=False,
        roles=[manager_role],
        assigned_branch_id="BR-101",
    )
    analyst_user = User(
        email="analyst@bank.internal",
        hashed_password=hash_password("AnalystPass123!"),
        full_name="Analyst User",
        is_active=True,
        is_superuser=False,
        roles=[analyst_role],
    )
    db_session.add_all([admin_user, manager_user, analyst_user])
    await db_session.flush()

    # Dashboards
    dash_exec = Dashboard(
        slug="exec-overview",
        title="Executive Overview",
        description="High level metrics",
        category="Executive",
        superset_dashboard_id="uuid-exec-1",
        is_active=True,
        allowed_roles=[admin_role],
    )
    dash_branch = Dashboard(
        slug="branch-metrics",
        title="Branch Metrics",
        description="Branch operations",
        category="Operations",
        superset_dashboard_id="uuid-branch-1",
        is_active=True,
        allowed_roles=[admin_role, manager_role],
        requires_branch_scope=True,
    )
    dash_analyst = Dashboard(
        slug="analyst-risk",
        title="Credit Risk",
        description="Credit metrics",
        category="Risk",
        superset_dashboard_id="uuid-risk-1",
        is_active=True,
        allowed_roles=[admin_role, analyst_role],
    )
    db_session.add_all([dash_exec, dash_branch, dash_analyst])
    await db_session.commit()

    return {
        "admin_user": admin_user,
        "manager_user": manager_user,
        "analyst_user": analyst_user,
        "dash_exec": dash_exec,
        "dash_branch": dash_branch,
        "dash_analyst": dash_analyst,
    }
