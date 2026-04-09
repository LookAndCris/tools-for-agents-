"""Tests for repository ABC contracts — shape verification and infra isolation."""
from __future__ import annotations

import inspect
from abc import ABC

import pytest


class TestAppointmentRepositoryShape:
    def test_is_abstract(self):
        from domain.repositories.appointment_repository import AppointmentRepository
        assert issubclass(AppointmentRepository, ABC)
        assert inspect.isabstract(AppointmentRepository)

    def test_has_get_by_id(self):
        from domain.repositories.appointment_repository import AppointmentRepository
        assert hasattr(AppointmentRepository, "get_by_id")

    def test_has_save(self):
        from domain.repositories.appointment_repository import AppointmentRepository
        assert hasattr(AppointmentRepository, "save")

    def test_has_find_by_staff_and_date_range(self):
        from domain.repositories.appointment_repository import AppointmentRepository
        assert hasattr(AppointmentRepository, "find_by_staff_and_date_range")

    def test_has_find_by_client(self):
        from domain.repositories.appointment_repository import AppointmentRepository
        assert hasattr(AppointmentRepository, "find_by_client")

    def test_cannot_be_instantiated(self):
        from domain.repositories.appointment_repository import AppointmentRepository
        with pytest.raises(TypeError):
            AppointmentRepository()  # type: ignore


class TestServiceRepositoryShape:
    def test_is_abstract(self):
        from domain.repositories.service_repository import ServiceRepository
        assert issubclass(ServiceRepository, ABC)
        assert inspect.isabstract(ServiceRepository)

    def test_has_required_methods(self):
        from domain.repositories.service_repository import ServiceRepository
        assert hasattr(ServiceRepository, "get_by_id")
        assert hasattr(ServiceRepository, "get_all_active")
        assert hasattr(ServiceRepository, "find_by_ids")


class TestStaffRepositoryShape:
    def test_is_abstract(self):
        from domain.repositories.staff_repository import StaffRepository
        assert issubclass(StaffRepository, ABC)
        assert inspect.isabstract(StaffRepository)

    def test_has_required_methods(self):
        from domain.repositories.staff_repository import StaffRepository
        assert hasattr(StaffRepository, "get_by_id")
        assert hasattr(StaffRepository, "find_by_service")


class TestClientRepositoryShape:
    def test_is_abstract(self):
        from domain.repositories.client_repository import ClientRepository
        assert issubclass(ClientRepository, ABC)
        assert inspect.isabstract(ClientRepository)

    def test_has_required_methods(self):
        from domain.repositories.client_repository import ClientRepository
        assert hasattr(ClientRepository, "get_by_id")
        assert hasattr(ClientRepository, "get_by_user_id")


class TestStaffAvailabilityRepositoryShape:
    def test_is_abstract(self):
        from domain.repositories.staff_availability_repository import StaffAvailabilityRepository
        assert issubclass(StaffAvailabilityRepository, ABC)
        assert inspect.isabstract(StaffAvailabilityRepository)

    def test_has_required_methods(self):
        from domain.repositories.staff_availability_repository import StaffAvailabilityRepository
        assert hasattr(StaffAvailabilityRepository, "get_by_staff")
        assert hasattr(StaffAvailabilityRepository, "get_by_staff_and_day")


class TestStaffTimeOffRepositoryShape:
    def test_is_abstract(self):
        from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
        assert issubclass(StaffTimeOffRepository, ABC)
        assert inspect.isabstract(StaffTimeOffRepository)

    def test_has_required_methods(self):
        from domain.repositories.staff_time_off_repository import StaffTimeOffRepository
        assert hasattr(StaffTimeOffRepository, "get_by_staff_and_range")


class TestRepositoryInfraIsolation:
    def test_appointment_repo_no_infra_imports(self):
        """AppointmentRepository must not import any infrastructure modules."""
        import domain.repositories.appointment_repository as mod
        source = inspect.getsource(mod)
        forbidden = ["sqlalchemy", "django", "psycopg", "redis", "boto", "requests"]
        for lib in forbidden:
            assert lib not in source, f"Found forbidden import '{lib}' in appointment_repository"

    def test_no_repo_imports_orm(self):
        """None of the repository ABCs should import ORM or DB libraries."""
        import domain.repositories.service_repository as mod_s
        import domain.repositories.staff_repository as mod_st
        import domain.repositories.client_repository as mod_c
        for mod in [mod_s, mod_st, mod_c]:
            source = inspect.getsource(mod)
            for lib in ["sqlalchemy", "django", "psycopg2", "motor"]:
                assert lib not in source
