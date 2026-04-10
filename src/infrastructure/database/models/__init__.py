"""Models package — importing all models here ensures Alembic discovers them
for autogenerate and that ``Base.metadata`` contains all table definitions."""

from infrastructure.database.models.role import RoleModel
from infrastructure.database.models.user import UserModel
from infrastructure.database.models.service import ServiceModel
from infrastructure.database.models.staff_profile import StaffProfileModel
from infrastructure.database.models.staff_service import StaffServiceModel
from infrastructure.database.models.client_profile import ClientProfileModel
from infrastructure.database.models.staff_availability import StaffAvailabilityModel
from infrastructure.database.models.staff_time_off import StaffTimeOffModel
from infrastructure.database.models.appointment import AppointmentModel
from infrastructure.database.models.appointment_event import AppointmentEventModel
from infrastructure.database.models.waitlist_entry import WaitlistEntryModel
from infrastructure.database.models.waitlist_notification import WaitlistNotificationModel

__all__ = [
    "RoleModel",
    "UserModel",
    "ServiceModel",
    "StaffProfileModel",
    "StaffServiceModel",
    "ClientProfileModel",
    "StaffAvailabilityModel",
    "StaffTimeOffModel",
    "AppointmentModel",
    "AppointmentEventModel",
    "WaitlistEntryModel",
    "WaitlistNotificationModel",
]
