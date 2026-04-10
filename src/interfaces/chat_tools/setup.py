"""Tool registration — wire all 14 in-scope tools into the shared ToolRegistry.

Import this module to ensure all tools are registered. The ``registry``
exported here is the singleton used by the chat-tools interface.

Tools registered (14 total):
  Service tools (4):
    - search_services
    - get_service_details
    - get_service_price        (derived)
    - get_service_duration     (derived)

  Staff tools (1):
    - find_available_staff

  Slot tools (1):
    - find_available_slots

  Appointment tools (4):
    - create_appointment       (mutation)
    - cancel_appointment       (mutation)
    - reschedule_appointment   (mutation)
    - get_client_appointments

  Staff time tools (2):
    - block_staff_time         (mutation)
    - unblock_staff_time       (mutation)

  Waitlist tools (2):
    - add_waitlist             (mutation)
    - notify_waitlist          (mutation)
"""
from __future__ import annotations

from infrastructure.database.session import async_session_factory
from interfaces.chat_tools.executor import ToolExecutor
from interfaces.chat_tools.registry import ToolRegistry

from interfaces.chat_tools.dependencies import (
    make_add_waitlist_uc,
    make_block_staff_time_uc,
    make_cancel_appointment_uc,
    make_create_appointment_uc,
    make_find_available_slots_uc,
    make_find_available_staff_uc,
    make_get_client_appointments_uc,
    make_get_service_details_uc,
    make_list_services_uc,
    make_notify_waitlist_uc,
    make_reschedule_appointment_uc,
    make_unblock_staff_time_uc,
)
from interfaces.chat_tools.tools.service_tools import (
    GetServiceDetailsInput,
    GetServiceDurationInput,
    GetServicePriceInput,
    SearchServicesInput,
    get_service_details,
    get_service_duration,
    get_service_price,
    search_services,
)
from interfaces.chat_tools.tools.staff_tools import (
    FindAvailableStaffInput,
    find_available_staff,
)
from interfaces.chat_tools.tools.slot_tools import (
    FindAvailableSlotsInput,
    find_available_slots,
)
from interfaces.chat_tools.tools.appointment_tools import (
    CancelAppointmentInput,
    CreateAppointmentInput,
    GetClientAppointmentsInput,
    RescheduleAppointmentInput,
    cancel_appointment,
    create_appointment,
    get_client_appointments,
    reschedule_appointment,
)
from interfaces.chat_tools.tools.staff_time_tools import (
    BlockStaffTimeInput,
    UnblockStaffTimeInput,
    block_staff_time,
    unblock_staff_time,
)
from interfaces.chat_tools.tools.waitlist_tools import (
    AddWaitlistInput,
    NotifyWaitlistInput,
    add_waitlist,
    notify_waitlist,
)

# ---------------------------------------------------------------------------
# Executor + shared global registry
# ---------------------------------------------------------------------------

executor = ToolExecutor(session_factory=async_session_factory)
registry = ToolRegistry(executor=executor)

# ---------------------------------------------------------------------------
# Service tools
# ---------------------------------------------------------------------------

registry.register(
    name="search_services",
    description="List all active services available for booking.",
    input_model=SearchServicesInput,
    handler=search_services,
    uc_factory=make_list_services_uc,
    is_mutation=False,
)

registry.register(
    name="get_service_details",
    description="Get full details for a specific service by its ID.",
    input_model=GetServiceDetailsInput,
    handler=get_service_details,
    uc_factory=make_get_service_details_uc,
    is_mutation=False,
)

registry.register(
    name="get_service_price",
    description="Get the price and currency for a specific service.",
    input_model=GetServicePriceInput,
    handler=get_service_price,
    uc_factory=make_get_service_details_uc,
    is_mutation=False,
)

registry.register(
    name="get_service_duration",
    description=(
        "Get the duration (in minutes) and buffer times for a specific service."
    ),
    input_model=GetServiceDurationInput,
    handler=get_service_duration,
    uc_factory=make_get_service_details_uc,
    is_mutation=False,
)

# ---------------------------------------------------------------------------
# Staff tools
# ---------------------------------------------------------------------------

registry.register(
    name="find_available_staff",
    description="Find staff members who offer a specific service.",
    input_model=FindAvailableStaffInput,
    handler=find_available_staff,
    uc_factory=make_find_available_staff_uc,
    is_mutation=False,
)

# ---------------------------------------------------------------------------
# Slot tools
# ---------------------------------------------------------------------------

registry.register(
    name="find_available_slots",
    description=(
        "Find available booking slots for a staff member within a date range "
        "(max 31 days)."
    ),
    input_model=FindAvailableSlotsInput,
    handler=find_available_slots,
    uc_factory=make_find_available_slots_uc,
    is_mutation=False,
)

# ---------------------------------------------------------------------------
# Appointment tools
# ---------------------------------------------------------------------------

registry.register(
    name="create_appointment",
    description="Book a new appointment for a client with a specific staff member.",
    input_model=CreateAppointmentInput,
    handler=create_appointment,
    uc_factory=make_create_appointment_uc,
    is_mutation=True,
)

registry.register(
    name="cancel_appointment",
    description="Cancel an existing appointment.",
    input_model=CancelAppointmentInput,
    handler=cancel_appointment,
    uc_factory=make_cancel_appointment_uc,
    is_mutation=True,
)

registry.register(
    name="reschedule_appointment",
    description="Move an existing appointment to a new time slot.",
    input_model=RescheduleAppointmentInput,
    handler=reschedule_appointment,
    uc_factory=make_reschedule_appointment_uc,
    is_mutation=True,
)

registry.register(
    name="get_client_appointments",
    description="List a client's appointments, optionally filtered by status.",
    input_model=GetClientAppointmentsInput,
    handler=get_client_appointments,
    uc_factory=make_get_client_appointments_uc,
    is_mutation=False,
)

# ---------------------------------------------------------------------------
# Staff time tools
# ---------------------------------------------------------------------------

registry.register(
    name="block_staff_time",
    description="Block a time period for a staff member (mark as unavailable).",
    input_model=BlockStaffTimeInput,
    handler=block_staff_time,
    uc_factory=make_block_staff_time_uc,
    is_mutation=True,
)

registry.register(
    name="unblock_staff_time",
    description="Remove a time-off block for a staff member.",
    input_model=UnblockStaffTimeInput,
    handler=unblock_staff_time,
    uc_factory=make_unblock_staff_time_uc,
    is_mutation=True,
)

# ---------------------------------------------------------------------------
# Waitlist tools
# ---------------------------------------------------------------------------

registry.register(
    name="add_waitlist",
    description="Add a client to the waitlist for a service.",
    input_model=AddWaitlistInput,
    handler=add_waitlist,
    uc_factory=make_add_waitlist_uc,
    is_mutation=True,
)

registry.register(
    name="notify_waitlist",
    description="Notify pending waitlist entries for a service in FIFO order.",
    input_model=NotifyWaitlistInput,
    handler=notify_waitlist,
    uc_factory=make_notify_waitlist_uc,
    is_mutation=True,
)
