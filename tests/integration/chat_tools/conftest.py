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
from types import SimpleNamespace

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


@pytest_asyncio.fixture
async def seeded_db(db_session: AsyncSession) -> SimpleNamespace:
    """Seed a consistent set of test data for chat tools tests.

    Returns a namespace with 3 services and 1 staff member.
    Uses unique names to avoid conflicts with existing seeded data.
    """
    # Use unique suffix to avoid constraint violations with existing data
    unique_suffix = uuid.uuid4().hex[:6]

    # Seed role and user for staff
    role = await seed_role(db_session, f"staff_{unique_suffix}")
    user = await seed_user(db_session, role.id)
    staff = await seed_staff_profile(db_session, user.id)

    # Seed services with unique names (no conflicts)
    from decimal import Decimal

    svc_corte = await seed_service(
        db_session,
        name=f"Service_Corte_{unique_suffix}",
        duration_minutes=45,
    )
    svc_corte.price = Decimal("250.00")

    svc_barba = await seed_service(
        db_session,
        name=f"Service_Barba_{unique_suffix}",
        duration_minutes=30,
    )
    svc_barba.price = Decimal("150.00")

    svc_afeitado = await seed_service(
        db_session,
        name=f"Service_Afeitado_{unique_suffix}",
        duration_minutes=30,
    )
    svc_afeitado.price = Decimal("120.00")

    # Link staff to service_corte only
    await seed_staff_service_link(db_session, staff.id, svc_corte.id)

    # Seed full-week availability for staff
    for day in range(1, 8):
        await seed_staff_availability(
            db_session,
            staff.id,
            day_of_week=day,
            start_time=time(8, 0),
            end_time=time(18, 0),
        )

    return SimpleNamespace(
        service_corte=svc_corte,
        service_barba=svc_barba,
        service_afeitado=svc_afeitado,
        staff_profile=staff,
    )


@pytest_asyncio.fixture
async def admin_ctx() -> AgentContext:
    """Alias for agent_ctx - returns admin context for tests."""
    return AgentContext(
        user_id=FIXED_USER_ID,
        role="admin",
        staff_id=FIXED_STAFF_UUID,
        client_id=None,
    )
