"""Unit tests for StaffTimeOff domain entity (Task 5.1 - RED phase)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from domain.value_objects.time_slot import TimeSlot


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


def _make_slot(start_hour: int = 9, end_hour: int = 17) -> TimeSlot:
    return TimeSlot(
        start=_utc(2026, 5, 10, start_hour),
        end=_utc(2026, 5, 10, end_hour),
    )


class TestStaffTimeOffCreation:
    """Tests for StaffTimeOff entity construction."""

    def test_creates_with_required_fields(self):
        """StaffTimeOff can be created with id, staff_id, and time_slot."""
        from domain.entities.staff_time_off import StaffTimeOff

        entity = StaffTimeOff(
            id=uuid.uuid4(),
            staff_id=uuid.uuid4(),
            time_slot=_make_slot(),
        )
        assert entity.id is not None
        assert entity.staff_id is not None
        assert entity.time_slot is not None

    def test_creates_with_reason(self):
        """StaffTimeOff stores an optional reason string."""
        from domain.entities.staff_time_off import StaffTimeOff

        entity = StaffTimeOff(
            id=uuid.uuid4(),
            staff_id=uuid.uuid4(),
            time_slot=_make_slot(),
            reason="Annual leave",
        )
        assert entity.reason == "Annual leave"

    def test_reason_defaults_to_none(self):
        """StaffTimeOff reason is None when not provided."""
        from domain.entities.staff_time_off import StaffTimeOff

        entity = StaffTimeOff(
            id=uuid.uuid4(),
            staff_id=uuid.uuid4(),
            time_slot=_make_slot(),
        )
        assert entity.reason is None

    def test_stores_correct_staff_id(self):
        """StaffTimeOff preserves the staff_id it was given."""
        from domain.entities.staff_time_off import StaffTimeOff

        staff_id = uuid.uuid4()
        entity = StaffTimeOff(
            id=uuid.uuid4(),
            staff_id=staff_id,
            time_slot=_make_slot(),
        )
        assert entity.staff_id == staff_id

    def test_stores_correct_time_slot(self):
        """StaffTimeOff preserves the time_slot it was given."""
        from domain.entities.staff_time_off import StaffTimeOff

        slot = _make_slot(10, 14)
        entity = StaffTimeOff(
            id=uuid.uuid4(),
            staff_id=uuid.uuid4(),
            time_slot=slot,
        )
        assert entity.time_slot == slot
        assert entity.time_slot.start == _utc(2026, 5, 10, 10)
        assert entity.time_slot.end == _utc(2026, 5, 10, 14)


class TestStaffTimeOffRepositoryContract:
    """Tests that StaffTimeOffRepository ABC has the required save/delete methods."""

    def test_has_save_method(self):
        """StaffTimeOffRepository ABC must declare save()."""
        from domain.repositories.staff_time_off_repository import StaffTimeOffRepository

        assert hasattr(StaffTimeOffRepository, "save")

    def test_has_delete_method(self):
        """StaffTimeOffRepository ABC must declare delete()."""
        from domain.repositories.staff_time_off_repository import StaffTimeOffRepository

        assert hasattr(StaffTimeOffRepository, "delete")

    def test_has_get_by_id_method(self):
        """StaffTimeOffRepository ABC must declare get_by_id()."""
        from domain.repositories.staff_time_off_repository import StaffTimeOffRepository

        assert hasattr(StaffTimeOffRepository, "get_by_id")

    def test_cannot_be_instantiated(self):
        """StaffTimeOffRepository cannot be instantiated directly (is abstract)."""
        from domain.repositories.staff_time_off_repository import StaffTimeOffRepository

        with pytest.raises(TypeError):
            StaffTimeOffRepository()  # type: ignore
