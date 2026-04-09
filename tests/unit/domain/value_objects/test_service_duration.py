"""Tests for the ServiceDuration value object."""
import pytest
from domain.value_objects.service_duration import ServiceDuration
from domain.exceptions import InvalidServiceDurationError


class TestServiceDurationCreation:
    def test_valid_creation(self):
        sd = ServiceDuration(buffer_before=5, duration_minutes=60, buffer_after=10)
        assert sd.duration_minutes == 60
        assert sd.buffer_before == 5
        assert sd.buffer_after == 10

    def test_total_includes_buffers(self):
        sd = ServiceDuration(buffer_before=5, duration_minutes=60, buffer_after=10)
        assert sd.total == 75

    def test_zero_buffers_allowed(self):
        sd = ServiceDuration(buffer_before=0, duration_minutes=30, buffer_after=0)
        assert sd.total == 30

    def test_negative_duration_raises(self):
        with pytest.raises(InvalidServiceDurationError):
            ServiceDuration(buffer_before=0, duration_minutes=-1, buffer_after=0)

    def test_zero_duration_raises(self):
        with pytest.raises(InvalidServiceDurationError):
            ServiceDuration(buffer_before=0, duration_minutes=0, buffer_after=0)

    def test_negative_buffer_raises(self):
        with pytest.raises(InvalidServiceDurationError):
            ServiceDuration(buffer_before=-1, duration_minutes=30, buffer_after=0)

    def test_is_immutable(self):
        sd = ServiceDuration(buffer_before=0, duration_minutes=30, buffer_after=0)
        with pytest.raises((AttributeError, TypeError)):
            sd.duration_minutes = 60
