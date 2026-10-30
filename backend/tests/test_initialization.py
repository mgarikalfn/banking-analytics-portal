import gc
import os
import sqlite3
import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings, validate_signing_key
from app.core.database import Base
from app.core.exceptions import SupersetIntegrationError
from app.core.security import hash_password, verify_password
from app.main import init_default_data, validate_initial_admin_credentials
from app.models.dashboard import Dashboard
from app.models.role import Role
from app.models.user import User
from app.services.superset_service import SupersetService


def test_alembic_migration_upgrade_and_downgrade():
    """Verify that Alembic upgrade head creates all expected tables and downgrade removes them."""
    test_db_file = os.path.abspath("test_alembic_migration.db")
    if os.path.exists(test_db_file):
        try:
            os.remove(test_db_file)
        except OSError:
            pass

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option(
        "sqlalchemy.url", f"sqlite+aiosqlite:///{test_db_file}"
    )

    try:
        # Run upgrade head
        command.upgrade(alembic_cfg, "head")

        # Inspect SQLite schema directly using sqlite3
        conn = sqlite3.connect(test_db_file)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = {row[0] for row in cursor.fetchall()}

            expected_tables = {
                "alembic_version",
                "roles",
                "users",
                "user_roles",
                "dashboards",
                "dashboard_roles",
                "audit_logs",
            }
            assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"

            # Verify indexes exist on users table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='users'")
            user_indexes = {row[0] for row in cursor.fetchall()}
            assert "ix_users_email" in user_indexes
            assert "ix_users_id" in user_indexes

            # Verify indexes exist on dashboards table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='dashboards'")
            dash_indexes = {row[0] for row in cursor.fetchall()}
            assert "ix_dashboards_slug" in dash_indexes
            assert "ix_dashboards_id" in dash_indexes
        finally:
            conn.close()

        # Run downgrade base
        command.downgrade(alembic_cfg, "base")

        conn = sqlite3.connect(test_db_file)
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables_after = {row[0] for row in cursor.fetchall()}
            assert "roles" not in tables_after
            assert "users" not in tables_after
            assert "dashboards" not in tables_after
            assert "audit_logs" not in tables_after
        finally:
            conn.close()

    finally:
        gc.collect()
        if os.path.exists(test_db_file):
            try:
                os.remove(test_db_file)
            except OSError:
                pass


def test_validate_signing_keys_missing_short_and_placeholders():
    """Strictly reject missing, short, and placeholder signing keys."""
    # 1. Missing keys
    with pytest.raises(ValueError, match="SECRET_KEY is required"):
        validate_signing_key("SECRET_KEY", None)

    with pytest.raises(ValueError, match="SECRET_KEY is required"):
        validate_signing_key("SECRET_KEY", "   ")

    # 2. Too short (< 32 characters)
    with pytest.raises(ValueError, match="too short"):
        validate_signing_key("SECRET_KEY", "only-sixteen-chr")

    # 3. Known insecure patterns and placeholders
    insecure_keys = [
        "insecure-dev-secret-key-replace-in-production-32-chars-min",
        "REPLACE_WITH_YOUR_OWN_GENERATED_32_CHAR_SECRET_KEY_PLACEHOLDER",
        "change-this-secret-key-for-production-environment-32c",
        "configure_random_key_that_is_at_least_thirty_two_chars",
        "dev-secret-key-minimum-32-characters-long-for-testing",
        "example_secret_key_minimum_32_chars_long_placeholder",
    ]
    for key in insecure_keys:
        with pytest.raises(ValueError, match="contains known insecure or placeholder pattern"):
            validate_signing_key("SECRET_KEY", key)

    # 4. Valid 32+ character random key passes
    valid_key = "a1b2c3d4e5f678901234567890abcdefa1b2c3d4e5f678901234567890abcdef"
    assert validate_signing_key("SECRET_KEY", valid_key) == valid_key


def test_settings_validate_security_keys_method(monkeypatch):
    """Calling settings.validate_security_keys() validates both SECRET_KEY and CSRF_SECRET_KEY."""
    monkeypatch.setattr(settings, "SECRET_KEY", None)
    with pytest.raises(ValueError, match="SECRET_KEY is required"):
        settings.validate_security_keys()

    monkeypatch.setattr(settings, "SECRET_KEY", "a1b2c3d4e5f678901234567890abcdefa1b2c3d4e5f678901234567890abcdef")
    monkeypatch.setattr(settings, "CSRF_SECRET_KEY", "insecure-csrf-key-placeholder-1234567890")
    with pytest.raises(ValueError, match="CSRF_SECRET_KEY contains known insecure or placeholder pattern"):
        settings.validate_security_keys()


@pytest.mark.asyncio
async def test_validate_initial_admin_credentials():
    """Verify password safety checks for initial administrator configuration."""
    # Missing email
    with pytest.raises(ValueError, match="FIRST_SUPERUSER_EMAIL is required"):
        validate_initial_admin_credentials("", "ValidP@ssw0rd123!")

    # Missing or short password (< 8 chars)
    short_passwords = ["", "short", "1234567", "admin"]
    for pwd in short_passwords:
        with pytest.raises(ValueError, match="at least 8 characters"):
            validate_initial_admin_credentials("admin@bank.internal", pwd)

    # Known insecure defaults and placeholders (>= 8 chars)
    insecure_defaults = [
        "password",
        "password123",
        "AdminBanking123!",
        "ChangeThisPassword123!",
        "admin_password_placeholder",
        "my_placeholder_pwd",
        "12345678",
        "qwerty1234",
        "REPLACE_WITH_YOUR_OWN_STRONG_PASSWORD_PLACEHOLDER",
        "ConfigureAStrongInitialPassword123!",
    ]
    for pwd in insecure_defaults:
        with pytest.raises(ValueError, match="cannot be a known default or placeholder"):
            validate_initial_admin_credentials("admin@bank.internal", pwd)

    # Valid, strong password passes without exception
    validate_initial_admin_credentials("admin@bank.internal", "SecureBank#Pass987!")


@pytest.mark.asyncio
async def test_seed_idempotency_preserves_existing_password(monkeypatch):
    """Subsequent startups must not overwrite existing administrator password or duplicate data."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async_session = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Monkeypatch session factory and settings for first seed
    monkeypatch.setattr("app.main.async_session_factory", async_session)
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_EMAIL", "seedadmin@bank.internal")
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_PASSWORD", "InitialStrongP@ss123!")

    # First seed run
    await init_default_data()

    # Inspect created user
    async with async_session() as session:
        res = await session.execute(
            select(User).where(User.email == "seedadmin@bank.internal")
        )
        user = res.scalars().first()
        assert user is not None
        assert user.is_superuser is True
        initial_hash = user.hashed_password
        initial_id = user.id
        assert verify_password("InitialStrongP@ss123!", initial_hash)

        # Check roles and dashboards count
        roles_count = len((await session.execute(select(Role))).scalars().all())
        dash_count = len((await session.execute(select(Dashboard))).scalars().all())

    # Second seed run with a DIFFERENT configured password in environment
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_PASSWORD", "AttemptedOverwriteP@ss456!")
    await init_default_data()

    # Verify password was NOT changed and duplicate records were not added
    async with async_session() as session:
        res = await session.execute(
            select(User).where(User.email == "seedadmin@bank.internal")
        )
        user_after = res.scalars().first()
        assert user_after.id == initial_id
        assert user_after.hashed_password == initial_hash
        assert verify_password("InitialStrongP@ss123!", user_after.hashed_password)
        assert not verify_password("AttemptedOverwriteP@ss456!", user_after.hashed_password)

        roles_count_after = len((await session.execute(select(Role))).scalars().all())
        dash_count_after = len((await session.execute(select(Dashboard))).scalars().all())
        assert roles_count == roles_count_after
        assert dash_count == dash_count_after

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_seed_missing_admin_config_raises_error(monkeypatch):
    """When no admin exists and configuration is missing, initialization must fail cleanly."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async_session = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    monkeypatch.setattr("app.main.async_session_factory", async_session)
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_EMAIL", None)
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_PASSWORD", None)

    with pytest.raises(ValueError, match="FIRST_SUPERUSER_EMAIL is required"):
        await init_default_data()

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_seed_collision_with_existing_non_superuser_fails_safely(monkeypatch):
    """If a non-superuser user already exists with FIRST_SUPERUSER_EMAIL, fail cleanly without promoting."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    async_session = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 1. Pre-create a regular (non-superuser) account
    existing_user_pwd = "UserOriginalSecurePassword999!"
    async with async_session() as session:
        regular_user = User(
            email="collision@bank.internal",
            hashed_password=hash_password(existing_user_pwd),
            full_name="Regular Staff Member",
            is_active=True,
            is_superuser=False,
        )
        session.add(regular_user)
        await session.commit()
        original_hash = regular_user.hashed_password
        original_id = regular_user.id

    # 2. Attempt to initialize superuser with the SAME email address
    monkeypatch.setattr("app.main.async_session_factory", async_session)
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_EMAIL", "collision@bank.internal")
    monkeypatch.setattr(settings, "FIRST_SUPERUSER_PASSWORD", "NewAdminSecurePassword777!")

    # Must raise a clear collision error
    with pytest.raises(ValueError, match="Account collision"):
        await init_default_data()

    # 3. Verify the existing user was preserved: NOT promoted, password unchanged
    async with async_session() as session:
        res = await session.execute(
            select(User).where(User.email == "collision@bank.internal")
        )
        user_after = res.scalars().first()
        assert user_after is not None
        assert user_after.id == original_id
        assert user_after.is_superuser is False  # NOT promoted!
        assert user_after.hashed_password == original_hash
        assert verify_password(existing_user_pwd, user_after.hashed_password)
        assert not verify_password("NewAdminSecurePassword777!", user_after.hashed_password)

        # Confirm no superusers exist in the system
        superusers = (
            await session.execute(select(User).where(User.is_superuser == True))
        ).scalars().all()
        assert len(superusers) == 0

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_superset_unconfigured_behaviour():
    """SupersetService correctly reports unconfigured status and prevents invalid API calls."""
    # Test with empty credentials
    unconfigured_svc = SupersetService(
        base_url="http://localhost:8088",
        admin_username="",
        admin_password="",
    )
    assert not unconfigured_svc.is_configured()

    health = await unconfigured_svc.check_health()
    assert health["configured"] is False
    assert health["connected"] is False
    assert "Unconfigured" in health["status_detail"]

    with pytest.raises(SupersetIntegrationError, match="not configured"):
        await unconfigured_svc.get_admin_token()

    # Test with placeholder credentials
    placeholder_svc = SupersetService(
        base_url="http://localhost:8088",
        admin_username="admin",
        admin_password="admin_password_placeholder",
    )
    assert not placeholder_svc.is_configured()
