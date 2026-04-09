"""Value objects package — immutable domain primitives."""
from domain.value_objects.time_slot import TimeSlot
from domain.value_objects.money import Money
from domain.value_objects.service_duration import ServiceDuration
from domain.value_objects.appointment_status import AppointmentStatus

__all__ = [
    "TimeSlot",
    "Money",
    "ServiceDuration",
    "AppointmentStatus",
]
