"""Tests for WaitlistStatus value object (Task 1.1 — RED phase)."""
from __future__ import annotations

import pytest


class TestWaitlistStatusValues:
    def test_pending_value(self):
        from domain.value_objects.waitlist_status import WaitlistStatus
        assert WaitlistStatus.PENDING == "pending"

    def test_notified_value(self):
        from domain.value_objects.waitlist_status import WaitlistStatus
        assert WaitlistStatus.NOTIFIED == "notified"

    def test_expired_value(self):
        from domain.value_objects.waitlist_status import WaitlistStatus
        assert WaitlistStatus.EXPIRED == "expired"

    def test_cancelled_value(self):
        from domain.value_objects.waitlist_status import WaitlistStatus
        assert WaitlistStatus.CANCELLED == "cancelled"

    def test_is_str_enum(self):
        from domain.value_objects.waitlist_status import WaitlistStatus
        assert isinstance(WaitlistStatus.PENDING, str)

    def test_all_four_values_exist(self):
        from domain.value_objects.waitlist_status import WaitlistStatus
        names = {s.name for s in WaitlistStatus}
        assert names == {"PENDING", "NOTIFIED", "EXPIRED", "CANCELLED"}
