"""Entities package — domain objects with identity and lifecycle."""
from domain.entities.appointment import Appointment
from domain.entities.user import User
from domain.entities.service import Service
from domain.entities.staff import Staff
from domain.entities.client import Client
from domain.entities.waitlist_entry import WaitlistEntry
from domain.entities.waitlist_notification import WaitlistNotification

__all__ = [
    "Appointment",
    "User",
    "Service",
    "Staff",
    "Client",
    "WaitlistEntry",
    "WaitlistNotification",
]
