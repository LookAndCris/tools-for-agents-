"""Chat tools dependency injection factories.

Mirrors ``interfaces/api/dependencies.py`` but returns ``(AsyncSession, UseCase)``
tuples instead of using FastAPI ``Depends``.  The session lifecycle is owned
by the caller (typically ``ToolExecutor``).

Each factory accepts an already-open ``AsyncSession`` and wires the
repositories and use case that the corresponding tool needs.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases.add_waitlist import AddWaitlistUseCase
from application.use_cases.block_staff_time import BlockStaffTimeUseCase
from application.use_cases.cancel_appointment import CancelAppointmentUseCase
from application.use_cases.create_appointment import CreateAppointmentUseCase
from application.use_cases.find_available_slots import FindAvailableSlotsUseCase
from application.use_cases.find_available_staff import FindAvailableStaffUseCase
from application.use_cases.get_client_appointments import GetClientAppointmentsUseCase
from application.use_cases.get_service_details import GetServiceDetailsUseCase
from application.use_cases.list_services import ListServicesUseCase
from application.use_cases.notify_waitlist import NotifyWaitlistUseCase
from application.use_cases.reschedule_appointment import RescheduleAppointmentUseCase
from application.use_cases.unblock_staff_time import UnblockStaffTimeUseCase
from infrastructure.repositories.pg_appointment_repo import PgAppointmentRepository
from infrastructure.repositories.pg_service_repo import PgServiceRepository
from infrastructure.repositories.pg_staff_availability_repo import PgStaffAvailabilityRepository
from infrastructure.repositories.pg_staff_repo import PgStaffRepository
from infrastructure.repositories.pg_client_repo import PgClientRepository
from infrastructure.repositories.pg_staff_time_off_repo import PgStaffTimeOffRepository
from infrastructure.repositories.pg_waitlist_entry_repo import PgWaitlistEntryRepository
from infrastructure.repositories.pg_waitlist_notification_repo import PgWaitlistNotificationRepository


# ---------------------------------------------------------------------------
# Service use case factories
# ---------------------------------------------------------------------------


def make_list_services_uc(session: AsyncSession) -> ListServicesUseCase:
    """Return a wired ``ListServicesUseCase`` for the given session."""
    return ListServicesUseCase(service_repo=PgServiceRepository(session))


def make_get_service_details_uc(session: AsyncSession) -> GetServiceDetailsUseCase:
    """Return a wired ``GetServiceDetailsUseCase`` for the given session."""
    return GetServiceDetailsUseCase(service_repo=PgServiceRepository(session))


# ---------------------------------------------------------------------------
# Staff use case factories
# ---------------------------------------------------------------------------


def make_find_available_staff_uc(session: AsyncSession) -> FindAvailableStaffUseCase:
    """Return a wired ``FindAvailableStaffUseCase`` for the given session."""
    return FindAvailableStaffUseCase(staff_repo=PgStaffRepository(session))


def make_find_available_slots_uc(session: AsyncSession) -> FindAvailableSlotsUseCase:
    """Return a wired ``FindAvailableSlotsUseCase`` for the given session."""
    return FindAvailableSlotsUseCase(
        service_repo=PgServiceRepository(session),
        availability_repo=PgStaffAvailabilityRepository(session),
        time_off_repo=PgStaffTimeOffRepository(session),
        appointment_repo=PgAppointmentRepository(session),
    )


# ---------------------------------------------------------------------------
# Appointment use case factories
# ---------------------------------------------------------------------------


def make_get_client_appointments_uc(session: AsyncSession) -> GetClientAppointmentsUseCase:
    """Return a wired ``GetClientAppointmentsUseCase`` for the given session."""
    return GetClientAppointmentsUseCase(appointment_repo=PgAppointmentRepository(session))


def make_create_appointment_uc(session: AsyncSession) -> CreateAppointmentUseCase:
    """Return a wired ``CreateAppointmentUseCase`` for the given session."""
    return CreateAppointmentUseCase(
        service_repo=PgServiceRepository(session),
        staff_repo=PgStaffRepository(session),
        availability_repo=PgStaffAvailabilityRepository(session),
        time_off_repo=PgStaffTimeOffRepository(session),
        appointment_repo=PgAppointmentRepository(session),
    )


def make_cancel_appointment_uc(session: AsyncSession) -> CancelAppointmentUseCase:
    """Return a wired ``CancelAppointmentUseCase`` for the given session."""
    return CancelAppointmentUseCase(appointment_repo=PgAppointmentRepository(session))


def make_reschedule_appointment_uc(session: AsyncSession) -> RescheduleAppointmentUseCase:
    """Return a wired ``RescheduleAppointmentUseCase`` for the given session."""
    return RescheduleAppointmentUseCase(
        appointment_repo=PgAppointmentRepository(session),
        service_repo=PgServiceRepository(session),
        availability_repo=PgStaffAvailabilityRepository(session),
        time_off_repo=PgStaffTimeOffRepository(session),
    )


# ---------------------------------------------------------------------------
# Staff time off use case factories
# ---------------------------------------------------------------------------


def make_block_staff_time_uc(session: AsyncSession) -> BlockStaffTimeUseCase:
    """Return a wired ``BlockStaffTimeUseCase`` for the given session."""
    return BlockStaffTimeUseCase(
        staff_repo=PgStaffRepository(session),
        time_off_repo=PgStaffTimeOffRepository(session),
    )


def make_unblock_staff_time_uc(session: AsyncSession) -> UnblockStaffTimeUseCase:
    """Return a wired ``UnblockStaffTimeUseCase`` for the given session."""
    return UnblockStaffTimeUseCase(time_off_repo=PgStaffTimeOffRepository(session))


# ---------------------------------------------------------------------------
# Waitlist use case factories
# ---------------------------------------------------------------------------


def make_add_waitlist_uc(session: AsyncSession) -> AddWaitlistUseCase:
    """Return a wired ``AddWaitlistUseCase`` for the given session."""
    return AddWaitlistUseCase(
        service_repo=PgServiceRepository(session),
        staff_repo=PgStaffRepository(session),
        waitlist_repo=PgWaitlistEntryRepository(session),
        client_repo=PgClientRepository(session),
    )


def make_notify_waitlist_uc(session: AsyncSession) -> NotifyWaitlistUseCase:
    """Return a wired ``NotifyWaitlistUseCase`` for the given session."""
    return NotifyWaitlistUseCase(
        waitlist_repo=PgWaitlistEntryRepository(session),
        notification_repo=PgWaitlistNotificationRepository(session),
    )
