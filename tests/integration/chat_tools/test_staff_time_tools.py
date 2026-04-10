"""Integration tests for staff time tool handlers (T20, T21, T22).

Tests call tool handler functions DIRECTLY with the test-scoped db_session,
wiring use cases via the dependency factories from interfaces.chat_tools.dependencies.
This bypasses ToolExecutor entirely so the test session owns the transaction.

Scenarios:
  T20 — block_staff_time creates a time-off record for the given window
  T21 — blocked time is excluded from find_available_slots results
  T22 — unblocking restores slot availability
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from application.dto.responses import AvailableSlotsResponse, StaffTimeOffResponse
from interfaces.chat_tools.context import AgentContext
from interfaces.chat_tools.dependencies import (
    make_block_staff_time_uc,
    make_find_available_slots_uc,
    make_unblock_staff_time_uc,
)
from interfaces.chat_tools.tools.slot_tools import FindAvailableSlotsInput, find_available_slots
from interfaces.chat_tools.tools.staff_time_tools import (
    BlockStaffTimeInput,
    UnblockStaffTimeInput,
    block_staff_time,
    unblock_staff_time,
)
from tests.integration.chat_tools.conftest import (
    FIXED_STAFF_UUID,
    seed_staff_with_service,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _next_monday() -> date:
    """Return the date of the next Monday (always at least 1 day ahead)."""
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    return today + timedelta(days=days_until_monday)


def _utc(d: date, hour: int, minute: int = 0) -> datetime:
    """Build a UTC-aware datetime from a date and time components."""
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# T20 — block_staff_time success
# ---------------------------------------------------------------------------


async def test_block_staff_time_success(
    db_session: AsyncSession,
    agent_ctx: AgentContext,
) -> None:
    """T20: block_staff_time returns a StaffTimeOffResponse with id, staff_id, and correct time range."""
    # Seed: staff profile (no service needed for block)
    staff, _ = await seed_staff_with_service(db_session, staff_id=FIXED_STAFF_UUID)

    monday = _next_monday()
    start = _utc(monday, 11)
    end = _utc(monday, 12)

    inp = BlockStaffTimeInput(
        staff_id=staff.id,
        start_time=start,
        end_time=end,
        reason="T20 test block",
    )
    uc = make_block_staff_time_uc(db_session)

    result = await block_staff_time(agent_ctx, inp, uc)

    # Assert: returns a StaffTimeOffResponse
    assert isinstance(result, StaffTimeOffResponse)
    # Assert: has an id
    assert result.id is not None
    # Assert: staff_id matches
    assert result.staff_id == staff.id
    # Assert: time range is preserved
    assert result.start_time == start
    assert result.end_time == end


# ---------------------------------------------------------------------------
# T21 — blocked time excluded from available slots
# ---------------------------------------------------------------------------


async def test_blocked_time_excluded_from_available_slots(
    db_session: AsyncSession,
    agent_ctx: AgentContext,
) -> None:
    """T21: after blocking 11:00-12:00 on Monday, slots overlapping that window are absent.

    Slots outside the blocked window (e.g. 08:00-11:00 and 12:00-18:00) must still appear.
    """
    staff, svc = await seed_staff_with_service(db_session, staff_id=FIXED_STAFF_UUID)

    monday = _next_monday()
    block_start = _utc(monday, 11)
    block_end = _utc(monday, 12)

    # Block 11:00-12:00
    block_inp = BlockStaffTimeInput(
        staff_id=staff.id,
        start_time=block_start,
        end_time=block_end,
        reason="T21 test block",
    )
    block_uc = make_block_staff_time_uc(db_session)
    await block_staff_time(agent_ctx, block_inp, block_uc)

    # Find available slots for that Monday
    slots_inp = FindAvailableSlotsInput(
        staff_id=staff.id,
        service_id=svc.id,
        date_from=monday,
        date_to=monday,
    )
    slots_uc = make_find_available_slots_uc(db_session)
    result = await find_available_slots(agent_ctx, slots_inp, slots_uc)

    assert isinstance(result, AvailableSlotsResponse)
    slots: list[datetime] = result.slots

    # No slot that overlaps the blocked 11:00-12:00 window should appear.
    # A 60-minute service slot overlaps if: slot_start < block_end AND slot_start + 60min > block_start.
    # Simplification: any slot starting at 11:00 (and up to but not including 12:00)
    # would conflict with a 60-min service.  Since duration=60min:
    #   slot at 11:00 ends at 12:00 — conflicts with block 11:00-12:00
    #   slot at 10:30 ends at 11:30 — also overlaps
    # The slot_finder should exclude any slot whose [start, start+duration) overlaps [11:00, 12:00).
    for slot in slots:
        slot_end = slot + timedelta(hours=1)  # service duration = 60 min
        overlaps = slot < block_end and slot_end > block_start
        assert not overlaps, (
            f"Slot {slot.isoformat()} overlaps blocked window "
            f"{block_start.isoformat()}–{block_end.isoformat()}"
        )

    # Slots before the block (e.g. 08:00–10:00) must still be present
    morning_slots = [s for s in slots if s < block_start]
    assert len(morning_slots) > 0, "Expected morning slots before the blocked window"

    # Slots after the block (e.g. 12:00 onwards) must still be present
    afternoon_slots = [s for s in slots if s >= block_end]
    assert len(afternoon_slots) > 0, "Expected afternoon slots after the blocked window"


# ---------------------------------------------------------------------------
# T22 — unblock restores slot availability
# ---------------------------------------------------------------------------


async def test_unblock_staff_time_restores_availability(
    db_session: AsyncSession,
    agent_ctx: AgentContext,
) -> None:
    """T22: after blocking and then unblocking 11:00-12:00, slots in that window are restored."""
    staff, svc = await seed_staff_with_service(db_session, staff_id=FIXED_STAFF_UUID)

    monday = _next_monday()
    block_start = _utc(monday, 11)
    block_end = _utc(monday, 12)

    # --- Step 1: Block 11:00-12:00 ---
    block_inp = BlockStaffTimeInput(
        staff_id=staff.id,
        start_time=block_start,
        end_time=block_end,
        reason="T22 test block",
    )
    block_uc = make_block_staff_time_uc(db_session)
    time_off = await block_staff_time(agent_ctx, block_inp, block_uc)
    assert isinstance(time_off, StaffTimeOffResponse)

    # --- Step 2: Unblock it ---
    unblock_inp = UnblockStaffTimeInput(time_off_id=time_off.id)
    unblock_uc = make_unblock_staff_time_uc(db_session)
    result = await unblock_staff_time(agent_ctx, unblock_inp, unblock_uc)

    # unblock_staff_time returns None on success
    assert result is None

    # --- Step 3: Find available slots — the previously blocked window should be back ---
    slots_inp = FindAvailableSlotsInput(
        staff_id=staff.id,
        service_id=svc.id,
        date_from=monday,
        date_to=monday,
    )
    slots_uc = make_find_available_slots_uc(db_session)
    slots_result = await find_available_slots(agent_ctx, slots_inp, slots_uc)

    assert isinstance(slots_result, AvailableSlotsResponse)
    slots: list[datetime] = slots_result.slots

    # There should be a slot at 11:00 (the previously blocked start)
    slot_starts = [s.replace(tzinfo=timezone.utc) if s.tzinfo is None else s for s in slots]
    assert block_start in slot_starts, (
        f"Expected slot at {block_start.isoformat()} after unblocking, "
        f"but available slots are: {[s.isoformat() for s in slot_starts]}"
    )
