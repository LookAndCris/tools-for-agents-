"""Domain repositories package — abstract persistence contracts."""
from domain.repositories.appointment_repository import AppointmentRepository
from domain.repositories.service_repository import ServiceRepository
from domain.repositories.staff_repository import StaffRepository
from domain.repositories.client_repository import ClientRepository
from domain.repositories.staff_availability_repository import StaffAvailabilityRepository
from domain.repositories.staff_time_off_repository import StaffTimeOffRepository

__all__ = [
    "AppointmentRepository",
    "ServiceRepository",
    "StaffRepository",
    "ClientRepository",
    "StaffAvailabilityRepository",
    "StaffTimeOffRepository",
]
