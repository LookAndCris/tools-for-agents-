"""SlotFinder — generates candidate appointment start times."""
from __future__ import annotations

from datetime import datetime, timedelta

from domain.entities.appointment import Appointment
from domain.scheduling_engine.conflict_resolver import ConflictResolver
from domain.value_objects.time_slot import TimeSlot


class SlotFinder:
    """
    Stateless service that generates valid appointment start times.

    For each available window, generates candidate start times at
    interval_minutes intervals, then filters out those that would conflict
    with existing appointments.
    """

    @staticmethod
    def find_slots(
        available_windows: list[TimeSlot],
        existing_appointments: list[Appointment],
        service_duration_minutes: int,
        interval_minutes: int = 30,
    ) -> list[datetime]:
        """
        Return sorted list of valid appointment start datetimes.

        For each available window:
        - Generate candidate start times at interval_minutes intervals.
        - For each candidate, create a TimeSlot(start, start + service_duration).
        - Check for conflicts using ConflictResolver.
        - Only include candidates with no conflicts.
        """
        valid_starts: list[datetime] = []
        duration = timedelta(minutes=service_duration_minutes)
        step = timedelta(minutes=interval_minutes)

        for window in available_windows:
            candidate = window.start
            while candidate + duration <= window.end:
                candidate_slot = TimeSlot(
                    start=candidate,
                    end=candidate + duration,
                )
                conflicts = ConflictResolver.find_conflicts(
                    candidate_slot, existing_appointments
                )
                if not conflicts:
                    valid_starts.append(candidate)
                candidate += step

        return sorted(valid_starts)
