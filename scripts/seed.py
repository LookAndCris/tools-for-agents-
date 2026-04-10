"""Seed script — populates the database with minimum data for the system to be usable.

Run from the project root (with .venv activated):
    python scripts/seed.py

The script is fully idempotent: it checks for existing rows before inserting,
so re-running it on an already-seeded database is safe and produces no duplicates.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import time
from decimal import Decimal
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the `src/` directory is on sys.path so that "infrastructure.*" imports
# resolve when running the script directly from the project root.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))

from sqlalchemy import select  # noqa: E402  (after sys.path patch)

from infrastructure.database.models import (  # noqa: E402
    ClientProfileModel,
    RoleModel,
    ServiceModel,
    StaffAvailabilityModel,
    StaffProfileModel,
    StaffServiceModel,
    UserModel,
)
from infrastructure.database.session import async_session_factory  # noqa: E402

# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

ROLES: list[dict] = [
    {"name": "admin",  "description": "Full system access"},
    {"name": "staff",  "description": "Staff member — manages own calendar and appointments"},
    {"name": "client", "description": "End customer — books and views own appointments"},
]

USERS: list[dict] = [
    {
        "email":      "admin@example.com",
        "first_name": "Ana",
        "last_name":  "García",
        "phone":      "+52 55 1000 0001",
        "role_name":  "admin",
    },
    {
        "email":      "staff@example.com",
        "first_name": "Carlos",
        "last_name":  "Martínez",
        "phone":      "+52 55 1000 0002",
        "role_name":  "staff",
    },
    {
        "email":      "client@example.com",
        "first_name": "Sofía",
        "last_name":  "López",
        "phone":      "+52 55 1000 0003",
        "role_name":  "client",
    },
]

SERVICES: list[dict] = [
    {
        "name":             "Corte de cabello",
        "description":      "Corte de cabello profesional para dama o caballero.",
        "duration_minutes": 45,
        "buffer_before":    5,
        "buffer_after":     10,
        "price":            Decimal("250.00"),
        "currency":         "MXN",
    },
    {
        "name":             "Manicure clásico",
        "description":      "Limpieza, lima y esmaltado de uñas de las manos.",
        "duration_minutes": 60,
        "buffer_before":    0,
        "buffer_after":     10,
        "price":            Decimal("180.00"),
        "currency":         "MXN",
    },
    {
        "name":             "Masaje relajante",
        "description":      "Masaje sueco de cuerpo completo para aliviar tensiones.",
        "duration_minutes": 60,
        "buffer_before":    10,
        "buffer_after":     15,
        "price":            Decimal("450.00"),
        "currency":         "MXN",
    },
]

# ISO weekday: 1=Monday … 5=Friday
WORKDAYS = [1, 2, 3, 4, 5]
WORK_START = time(9, 0)
WORK_END   = time(18, 0)


# ---------------------------------------------------------------------------
# Helper — get-or-create pattern
# ---------------------------------------------------------------------------

async def _get_or_create_role(session, name: str, description: str) -> RoleModel:
    result = await session.execute(select(RoleModel).where(RoleModel.name == name))
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  [skip]   role '{name}' already exists")
        return existing
    role = RoleModel(id=uuid.uuid4(), name=name, description=description)
    session.add(role)
    await session.flush()
    print(f"  [insert] role '{name}'")
    return role


async def _get_or_create_user(
    session,
    email: str,
    first_name: str,
    last_name: str,
    phone: str,
    role_id: uuid.UUID,
) -> UserModel:
    result = await session.execute(select(UserModel).where(UserModel.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  [skip]   user '{email}' already exists")
        return existing
    user = UserModel(
        id=uuid.uuid4(),
        role_id=role_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    print(f"  [insert] user '{email}'  ({first_name} {last_name})")
    return user


async def _get_or_create_staff_profile(session, user_id: uuid.UUID) -> StaffProfileModel:
    result = await session.execute(
        select(StaffProfileModel).where(StaffProfileModel.user_id == user_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  [skip]   staff_profile for user_id={user_id} already exists")
        return existing
    profile = StaffProfileModel(
        id=uuid.uuid4(),
        user_id=user_id,
        specialty="Estética integral",
        bio="Profesional con más de 5 años de experiencia en servicios de estética y bienestar.",
        is_available=True,
    )
    session.add(profile)
    await session.flush()
    print(f"  [insert] staff_profile for user_id={user_id}")
    return profile


async def _get_or_create_client_profile(session, user_id: uuid.UUID) -> ClientProfileModel:
    result = await session.execute(
        select(ClientProfileModel).where(ClientProfileModel.user_id == user_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  [skip]   client_profile for user_id={user_id} already exists")
        return existing
    profile = ClientProfileModel(
        id=uuid.uuid4(),
        user_id=user_id,
        preferred_staff_id=None,
        blocked_staff_ids=[],
        notes=None,
    )
    session.add(profile)
    await session.flush()
    print(f"  [insert] client_profile for user_id={user_id}")
    return profile


async def _get_or_create_service(session, data: dict) -> ServiceModel:
    result = await session.execute(
        select(ServiceModel).where(ServiceModel.name == data["name"])
    )
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  [skip]   service '{data['name']}' already exists")
        return existing
    service = ServiceModel(
        id=uuid.uuid4(),
        **data,
        is_active=True,
    )
    session.add(service)
    await session.flush()
    print(f"  [insert] service '{data['name']}' ({data['duration_minutes']} min, {data['price']} {data['currency']})")
    return service


async def _get_or_create_staff_service(
    session, staff_id: uuid.UUID, service_id: uuid.UUID, service_name: str
) -> StaffServiceModel:
    result = await session.execute(
        select(StaffServiceModel).where(
            StaffServiceModel.staff_id == staff_id,
            StaffServiceModel.service_id == service_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  [skip]   staff_service link for '{service_name}' already exists")
        return existing
    link = StaffServiceModel(
        id=uuid.uuid4(),
        staff_id=staff_id,
        service_id=service_id,
    )
    session.add(link)
    await session.flush()
    print(f"  [insert] staff_service link: staff={staff_id}, service='{service_name}'")
    return link


async def _get_or_create_availability(
    session, staff_id: uuid.UUID, day_of_week: int
) -> StaffAvailabilityModel:
    result = await session.execute(
        select(StaffAvailabilityModel).where(
            StaffAvailabilityModel.staff_id == staff_id,
            StaffAvailabilityModel.day_of_week == day_of_week,
        )
    )
    existing = result.scalar_one_or_none()
    day_names = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}
    day_label = day_names.get(day_of_week, str(day_of_week))
    if existing:
        print(f"  [skip]   availability for {day_label} already exists")
        return existing
    window = StaffAvailabilityModel(
        id=uuid.uuid4(),
        staff_id=staff_id,
        day_of_week=day_of_week,
        start_time=WORK_START,
        end_time=WORK_END,
    )
    session.add(window)
    await session.flush()
    print(f"  [insert] availability: {day_label} {WORK_START}-{WORK_END}")
    return window


# ---------------------------------------------------------------------------
# Main seed orchestration
# ---------------------------------------------------------------------------

async def seed() -> None:
    print("\n" + "=" * 60)
    print("  tools-for-agents — Database Seed")
    print("=" * 60)

    async with async_session_factory() as session:
        async with session.begin():

            # ------------------------------------------------------------------
            # 1. Roles
            # ------------------------------------------------------------------
            print("\n[1/6] Seeding roles…")
            role_map: dict[str, RoleModel] = {}
            for role_data in ROLES:
                role = await _get_or_create_role(session, **role_data)
                role_map[role.name] = role

            # ------------------------------------------------------------------
            # 2. Users
            # ------------------------------------------------------------------
            print("\n[2/6] Seeding users…")
            user_map: dict[str, UserModel] = {}
            for user_data in USERS:
                role_name = user_data["role_name"]
                role = role_map[role_name]
                user = await _get_or_create_user(
                    session,
                    email=user_data["email"],
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    phone=user_data["phone"],
                    role_id=role.id,
                )
                user_map[role_name] = user

            # ------------------------------------------------------------------
            # 3. Staff profile
            # ------------------------------------------------------------------
            print("\n[3/6] Seeding staff profile…")
            staff_user = user_map["staff"]
            staff_profile = await _get_or_create_staff_profile(session, staff_user.id)

            # ------------------------------------------------------------------
            # 4. Client profile
            # ------------------------------------------------------------------
            print("\n[4/6] Seeding client profile…")
            client_user = user_map["client"]
            await _get_or_create_client_profile(session, client_user.id)

            # ------------------------------------------------------------------
            # 5. Services + staff-service links
            # ------------------------------------------------------------------
            print("\n[5/6] Seeding services and staff-service links…")
            for service_data in SERVICES:
                service = await _get_or_create_service(session, service_data)
                await _get_or_create_staff_service(
                    session, staff_profile.id, service.id, service.name
                )

            # ------------------------------------------------------------------
            # 6. Weekly availability (Mon-Fri, 09:00-18:00)
            # ------------------------------------------------------------------
            print("\n[6/6] Seeding weekly availability (Mon–Fri 09:00–18:00)…")
            for day in WORKDAYS:
                await _get_or_create_availability(session, staff_profile.id, day)

    print("\n" + "=" * 60)
    print("  Seed completed successfully.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(seed())
