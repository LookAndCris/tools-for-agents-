"""Conftest for API integration tests.

Provides fixtures to spin up the FastAPI app with:
- a savepoint-isolated test database session (from the parent conftest)
- an auth bypass that returns a fixed UserContext without a DB lookup

Fixtures defined here:
  app         — configured FastAPI instance with dependency overrides
  client      — httpx.AsyncClient wrapping the ASGI app
  api_ctx     — a named tuple with seeded DB entities for tests that need data

All test sessions are isolated via the savepoint mechanism from
``tests/integration/conftest.py``.  No data written in one test leaks
into another.
"""
from __future__ import annotations

import uuid
from datetime import datetime, time, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.user_context import UserContext
from infrastructure.database.models.client_profile import ClientProfileModel
from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.service import ServiceModel
from infrastructure.database.models.staff_availability import StaffAvailabilityModel
from infrastructure.database.models.staff_profile import StaffProfileModel
from infrastructure.database.models.staff_service import StaffServiceModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.session import get_session
from interfaces.api.app import create_app
from interfaces.api.auth import get_current_user

# ---------------------------------------------------------------------------
# Fixed test identities — stable across all tests in a session
# ---------------------------------------------------------------------------

FIXED_USER_ID = uuid.uuid4()
FIXED_STAFF_UUID = uuid.uuid4()
FIXED_CLIENT_UUID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers — DB seeding functions
# ---------------------------------------------------------------------------


async def seed_role(session: AsyncSession, name: str) -> RoleModel:
    """Create and flush a role row."""
    role = RoleModel(id=uuid.uuid4(), name=f"{name}_{uuid.uuid4().hex[:6]}")
    session.add(role)
    await session.flush()
    return role


async def seed_user(
    session: AsyncSession,
    role_id: uuid.UUID,
    *,
    email: str | None = None,
) -> UserModel:
    """Create and flush a user row."""
    now = datetime.now(timezone.utc)
    user = UserModel(
        id=uuid.uuid4(),
        role_id=role_id,
        email=email or f"user_{uuid.uuid4().hex[:8]}@test.com",
        first_name="Test",
        last_name="User",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def seed_staff_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    is_available: bool = True,
) -> StaffProfileModel:
    """Create and flush a staff profile row."""
    now = datetime.now(timezone.utc)
    profile = StaffProfileModel(
        id=uuid.uuid4(),
        user_id=user_id,
        specialty="Test Specialty",
        bio="Test Bio",
        is_available=is_available,
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    await session.flush()
    return profile


async def seed_client_profile(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> ClientProfileModel:
    """Create and flush a client profile row."""
    now = datetime.now(timezone.utc)
    profile = ClientProfileModel(
        id=uuid.uuid4(),
        user_id=user_id,
        blocked_staff_ids=[],
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    await session.flush()
    return profile


async def seed_service(
    session: AsyncSession,
    *,
    name: str | None = None,
    duration_minutes: int = 60,
    is_active: bool = True,
) -> ServiceModel:
    """Create and flush a service row."""
    now = datetime.now(timezone.utc)
    svc = ServiceModel(
        id=uuid.uuid4(),
        name=name or f"Service_{uuid.uuid4().hex[:6]}",
        description="Test service description",
        duration_minutes=duration_minutes,
        buffer_before=0,
        buffer_after=0,
        price=Decimal("100.00"),
        currency="USD",
        is_active=is_active,
        created_at=now,
        updated_at=now,
    )
    session.add(svc)
    await session.flush()
    return svc


async def seed_staff_service_link(
    session: AsyncSession,
    staff_id: uuid.UUID,
    service_id: uuid.UUID,
) -> StaffServiceModel:
    """Link a staff member to a service."""
    link = StaffServiceModel(staff_id=staff_id, service_id=service_id)
    session.add(link)
    await session.flush()
    return link


async def seed_staff_availability(
    session: AsyncSession,
    staff_id: uuid.UUID,
    *,
    day_of_week: int = 1,
    start_time: time = time(8, 0),
    end_time: time = time(18, 0),
) -> StaffAvailabilityModel:
    """Create a weekly availability window for a staff member."""
    avail = StaffAvailabilityModel(
        id=uuid.uuid4(),
        staff_id=staff_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
    )
    session.add(avail)
    await session.flush()
    return avail


# ---------------------------------------------------------------------------
# App fixture — FastAPI instance with dependency overrides
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def app(db_session: AsyncSession):
    """Return a FastAPI app with test overrides for session and auth.

    - ``get_session`` is overridden to yield the savepoint-isolated test session.
    - ``get_current_user`` is overridden to return a fixed admin UserContext.
    """
    application = create_app()

    # Override auth — return a fixed admin caller (no DB lookup)
    def override_auth() -> UserContext:
        return UserContext(
            user_id=FIXED_USER_ID,
            role="admin",
            staff_id=FIXED_STAFF_UUID,
            client_id=FIXED_CLIENT_UUID,
        )

    # Override session — yield the savepoint-isolated test session
    async def override_session():
        yield db_session

    application.dependency_overrides[get_current_user] = override_auth
    application.dependency_overrides[get_session] = override_session

    return application


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(app):
    """Yield an httpx.AsyncClient wired to the test app via ASGITransport."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# No-auth client — uses real get_current_user (for testing 401 scenarios)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client_no_auth(db_session: AsyncSession):
    """Yield an httpx.AsyncClient that only overrides the session, not auth.

    Use this to test real authentication behavior (missing/invalid X-User-ID).
    """
    application = create_app()

    async def override_session():
        yield db_session

    application.dependency_overrides[get_session] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as c:
        yield c
