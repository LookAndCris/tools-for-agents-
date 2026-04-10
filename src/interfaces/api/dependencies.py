"""Per-request dependency injection factories.

Each function yields (or returns) a fully-wired use case by chaining
``Depends(get_session)`` → concrete repository constructors → use case constructor.

Usage in an endpoint::

    @router.get("/services")
    async def list_services(
        uc: ListServicesUseCase = Depends(get_list_services_uc),
    ) -> list[ServiceResponse]: ...
"""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases.add_waitlist import AddWaitlistUseCase
from application.use_cases.block_staff_time import BlockStaffTimeUseCase
from application.use_cases.cancel_appointment import CancelAppointmentUseCase
from application.use_cases.create_appointment import CreateAppointmentUseCase
from application.use_cases.find_available_slots import FindAvailableSlotsUseCase
from application.use_cases.find_available_staff import FindAvailableStaffUseCase
from application.use_cases.get_appointment_events import GetAppointmentEventsUseCase
from application.use_cases.get_client_appointments import GetClientAppointmentsUseCase
from application.use_cases.get_service_details import GetServiceDetailsUseCase
from application.use_cases.get_waitlist_entries import GetWaitlistEntriesUseCase
from application.use_cases.list_services import ListServicesUseCase
from application.use_cases.notify_waitlist import NotifyWaitlistUseCase
from application.use_cases.reschedule_appointment import RescheduleAppointmentUseCase
from application.use_cases.unblock_staff_time import UnblockStaffTimeUseCase
from infrastructure.database.session import get_session
from infrastructure.repositories.pg_appointment_repo import PgAppointmentRepository
from infrastructure.repositories.pg_client_repo import PgClientRepository
from infrastructure.repositories.pg_service_repo import PgServiceRepository
from infrastructure.repositories.pg_staff_availability_repo import PgStaffAvailabilityRepository
from infrastructure.repositories.pg_staff_repo import PgStaffRepository
from infrastructure.repositories.pg_staff_time_off_repo import PgStaffTimeOffRepository
from infrastructure.repositories.pg_waitlist_entry_repo import PgWaitlistEntryRepository
from infrastructure.repositories.pg_waitlist_notification_repo import PgWaitlistNotificationRepository

# Re-export auth dependency here for convenience (routers import from one place)
from interfaces.api.auth import get_current_user as get_current_user  # noqa: F401


# ---------------------------------------------------------------------------
# Service use cases
# ---------------------------------------------------------------------------


async def get_list_services_uc(
    session: AsyncSession = Depends(get_session),
) -> ListServicesUseCase:
    """Return a wired ``ListServicesUseCase`` for the current request."""
    return ListServicesUseCase(service_repo=PgServiceRepository(session))


async def get_service_details_uc(
    session: AsyncSession = Depends(get_session),
) -> GetServiceDetailsUseCase:
    """Return a wired ``GetServiceDetailsUseCase`` for the current request."""
    return GetServiceDetailsUseCase(service_repo=PgServiceRepository(session))


# ---------------------------------------------------------------------------
# Staff use cases
# ---------------------------------------------------------------------------


async def get_find_available_staff_uc(
    session: AsyncSession = Depends(get_session),
) -> FindAvailableStaffUseCase:
    """Return a wired ``FindAvailableStaffUseCase`` for the current request."""
    return FindAvailableStaffUseCase(staff_repo=PgStaffRepository(session))


async def get_find_available_slots_uc(
    session: AsyncSession = Depends(get_session),
) -> FindAvailableSlotsUseCase:
    """Return a wired ``FindAvailableSlotsUseCase`` for the current request."""
    return FindAvailableSlotsUseCase(
        service_repo=PgServiceRepository(session),
        availability_repo=PgStaffAvailabilityRepository(session),
        time_off_repo=PgStaffTimeOffRepository(session),
        appointment_repo=PgAppointmentRepository(session),
    )


# ---------------------------------------------------------------------------
# Appointment use cases
# ---------------------------------------------------------------------------


async def get_client_appointments_uc(
    session: AsyncSession = Depends(get_session),
) -> GetClientAppointmentsUseCase:
    """Return a wired ``GetClientAppointmentsUseCase`` for the current request."""
    return GetClientAppointmentsUseCase(appointment_repo=PgAppointmentRepository(session))


async def get_create_appointment_uc(
    session: AsyncSession = Depends(get_session),
) -> CreateAppointmentUseCase:
    """Return a wired ``CreateAppointmentUseCase`` for the current request."""
    return CreateAppointmentUseCase(
        service_repo=PgServiceRepository(session),
        staff_repo=PgStaffRepository(session),
        availability_repo=PgStaffAvailabilityRepository(session),
        time_off_repo=PgStaffTimeOffRepository(session),
        appointment_repo=PgAppointmentRepository(session),
    )


async def get_cancel_appointment_uc(
    session: AsyncSession = Depends(get_session),
) -> CancelAppointmentUseCase:
    """Return a wired ``CancelAppointmentUseCase`` for the current request."""
    return CancelAppointmentUseCase(appointment_repo=PgAppointmentRepository(session))


async def get_reschedule_appointment_uc(
    session: AsyncSession = Depends(get_session),
) -> RescheduleAppointmentUseCase:
    """Return a wired ``RescheduleAppointmentUseCase`` for the current request."""
    return RescheduleAppointmentUseCase(
        appointment_repo=PgAppointmentRepository(session),
        service_repo=PgServiceRepository(session),
        availability_repo=PgStaffAvailabilityRepository(session),
        time_off_repo=PgStaffTimeOffRepository(session),
    )


async def get_appointment_events_uc(
    session: AsyncSession = Depends(get_session),
) -> GetAppointmentEventsUseCase:
    """Return a wired ``GetAppointmentEventsUseCase`` for the current request."""
    return GetAppointmentEventsUseCase(appointment_repo=PgAppointmentRepository(session))


# ---------------------------------------------------------------------------
# Staff time off use cases
# ---------------------------------------------------------------------------


async def get_block_staff_time_uc(
    session: AsyncSession = Depends(get_session),
) -> BlockStaffTimeUseCase:
    """Return a wired ``BlockStaffTimeUseCase`` for the current request."""
    return BlockStaffTimeUseCase(
        staff_repo=PgStaffRepository(session),
        time_off_repo=PgStaffTimeOffRepository(session),
    )


async def get_unblock_staff_time_uc(
    session: AsyncSession = Depends(get_session),
) -> UnblockStaffTimeUseCase:
    """Return a wired ``UnblockStaffTimeUseCase`` for the current request."""
    return UnblockStaffTimeUseCase(time_off_repo=PgStaffTimeOffRepository(session))


# ---------------------------------------------------------------------------
# Waitlist use cases
# ---------------------------------------------------------------------------


async def get_add_waitlist_uc(
    session: AsyncSession = Depends(get_session),
) -> AddWaitlistUseCase:
    """Return a wired ``AddWaitlistUseCase`` for the current request."""
    return AddWaitlistUseCase(
        service_repo=PgServiceRepository(session),
        staff_repo=PgStaffRepository(session),
        waitlist_repo=PgWaitlistEntryRepository(session),
        client_repo=PgClientRepository(session),
    )


async def get_waitlist_entries_uc(
    session: AsyncSession = Depends(get_session),
) -> GetWaitlistEntriesUseCase:
    """Return a wired ``GetWaitlistEntriesUseCase`` for the current request."""
    return GetWaitlistEntriesUseCase(waitlist_repo=PgWaitlistEntryRepository(session))


async def get_notify_waitlist_uc(
    session: AsyncSession = Depends(get_session),
) -> NotifyWaitlistUseCase:
    """Return a wired ``NotifyWaitlistUseCase`` for the current request."""
    return NotifyWaitlistUseCase(
        waitlist_repo=PgWaitlistEntryRepository(session),
        notification_repo=PgWaitlistNotificationRepository(session),
    )
