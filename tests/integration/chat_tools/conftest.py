"""Conftest for chat_tools integration tests.

Provides shared fixtures for wiring tool handlers directly with the
savepoint-isolated test database session.

All tests bypass ToolExecutor and call handler functions directly,
passing use cases wired via the dependency factories.  This keeps
full session control in the test and avoids the OWN-session problem.

Fixtures defined here:
  agent_ctx       — a fixed AgentContext with admin role
  seeded_staff    — a fully seeded staff profile with service and availability
"""
from __future__ import annotations

import uuid
from datetime import datetime, time, timezone
from decimal import Decimal

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.service import ServiceModel
from infrastructure.database.models.staff_availability import StaffAvailabilityModel
from infrastructure.database.models.staff_profile import StaffProfileModel
from infrastructure.database.models.staff_service import StaffServiceModel
from infrastructure.database.models.user import UserModel
from interfaces.chat_tools.context import AgentContext

# ---------------------------------------------------------------------------
# Fixed test identities
# ---------------------------------------------------------------------------

FIXED_USER_ID = uuid.uuid4()
FIXED_STAFF_UUID = uuid.uuid4()


# ---------------------------------------------------------------------------
# Helpers — DB seeding functions
# ---------------------------------------------------------------------------


async def seed_role(session: AsyncSession, name: str) -> RoleModel:
    """Create and flush a role row."""
    role = RoleModel(id=uuid.uuid4(), name=f"{name}_{uuid.uuid4().hex[:6]}")
    session.add(role)
    await session.flush()
    return role


async def seed_user(session: AsyncSession, role_id: uuid.UUID) -> UserModel:
    """Create and flush a user row."""
    now = datetime.now(timezone.utc)
    user = UserModel(
        id=uuid.uuid4(),
        role_id=role_id,
        email=f"tool_user_{uuid.uuid4().hex[:8]}@test.com",
        first_name="Tool",
        last_name="Test",
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
    staff_id: uuid.UUID | None = None,
    is_available: bool = True,
) -> StaffProfileModel:
    """Create and flush a staff profile row."""
    now = datetime.now(timezone.utc)
    profile = StaffProfileModel(
        id=staff_id or uuid.uuid4(),
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
# Reusable setup helper
# ---------------------------------------------------------------------------


async def seed_staff_with_service(
    session: AsyncSession,
    *,
    staff_id: uuid.UUID | None = None,
    duration_minutes: int = 60,
) -> tuple[StaffProfileModel, ServiceModel]:
    """Seed a staff member with a service and full-week availability.

    Returns (staff_profile, service).
    """
    effective_staff_id = staff_id or uuid.uuid4()
    role = await seed_role(session, "tool_staff")
    user = await seed_user(session, role.id)
    staff = await seed_staff_profile(session, user.id, staff_id=effective_staff_id)
    svc = await seed_service(session, duration_minutes=duration_minutes)
    await seed_staff_service_link(session, staff.id, svc.id)

    # Seed availability for all 7 days so any weekday works
    for day in range(1, 8):
        await seed_staff_availability(
            session,
            staff.id,
            day_of_week=day,
            start_time=time(8, 0),
            end_time=time(18, 0),
        )

    return staff, svc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def agent_ctx() -> AgentContext:
    """Return a fixed AgentContext with admin role."""
    return AgentContext(
        user_id=FIXED_USER_ID,
        role="admin",
        staff_id=FIXED_STAFF_UUID,
        client_id=None,
    )
