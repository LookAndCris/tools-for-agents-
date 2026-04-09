"""initial schema

Revision ID: 001
Revises: —
Create Date: 2026-04-09

Creates all 10 core tables in dependency order:
  1. roles
  2. users                 (FK → roles)
  3. staff_profiles        (FK → users)
  4. client_profiles       (FK → users, staff_profiles)
  5. services
  6. staff_services        (FK → staff_profiles, services)
  7. staff_availability    (FK → staff_profiles)
  8. staff_time_off        (FK → staff_profiles)
  9. appointments          (FK → client_profiles, staff_profiles, services)
  10. appointment_events   (FK → appointments)
"""
from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None

# Shorthand for timezone-aware timestamp columns
_TS = sa.DateTime(timezone=True)


def _ts_col(name: str) -> sa.Column:
    """Return a TIMESTAMP WITH TIME ZONE column with a server default of now()."""
    return sa.Column(name, _TS, server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. roles
    # ------------------------------------------------------------------
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        _ts_col("created_at"),
        _ts_col("updated_at"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("name", name=op.f("uq_roles_name")),
    )

    # ------------------------------------------------------------------
    # 2. users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts_col("created_at"),
        _ts_col("updated_at"),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_users_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"], unique=False)

    # ------------------------------------------------------------------
    # 3. staff_profiles
    # ------------------------------------------------------------------
    op.create_table(
        "staff_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("specialty", sa.String(150), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts_col("created_at"),
        _ts_col("updated_at"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_staff_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staff_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_staff_profiles_user_id")),
    )
    op.create_index(op.f("ix_staff_profiles_user_id"), "staff_profiles", ["user_id"], unique=False)

    # ------------------------------------------------------------------
    # 4. client_profiles
    # ------------------------------------------------------------------
    op.create_table(
        "client_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preferred_staff_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "blocked_staff_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        _ts_col("created_at"),
        _ts_col("updated_at"),
        sa.ForeignKeyConstraint(
            ["preferred_staff_id"],
            ["staff_profiles.id"],
            name=op.f("fk_client_profiles_preferred_staff_id_staff_profiles"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_client_profiles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_client_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_client_profiles_user_id")),
    )
    op.create_index(
        op.f("ix_client_profiles_preferred_staff_id"),
        "client_profiles",
        ["preferred_staff_id"],
        unique=False,
    )
    op.create_index(op.f("ix_client_profiles_user_id"), "client_profiles", ["user_id"], unique=False)

    # ------------------------------------------------------------------
    # 5. services
    # ------------------------------------------------------------------
    op.create_table(
        "services",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("buffer_before", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("buffer_after", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="MXN"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        _ts_col("created_at"),
        _ts_col("updated_at"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_services")),
        sa.UniqueConstraint("name", name=op.f("uq_services_name")),
    )

    # ------------------------------------------------------------------
    # 6. staff_services  (junction)
    # ------------------------------------------------------------------
    op.create_table(
        "staff_services",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        _ts_col("created_at"),
        _ts_col("updated_at"),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name=op.f("fk_staff_services_service_id_services"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff_profiles.id"],
            name=op.f("fk_staff_services_staff_id_staff_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staff_services")),
        sa.UniqueConstraint(
            "staff_id", "service_id", name="uq_staff_services_staff_service"
        ),
    )
    op.create_index(op.f("ix_staff_services_service_id"), "staff_services", ["service_id"], unique=False)
    op.create_index(op.f("ix_staff_services_staff_id"), "staff_services", ["staff_id"], unique=False)

    # ------------------------------------------------------------------
    # 7. staff_availability
    # ------------------------------------------------------------------
    op.create_table(
        "staff_availability",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day_of_week", sa.SmallInteger(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        _ts_col("created_at"),
        _ts_col("updated_at"),
        sa.CheckConstraint(
            "day_of_week BETWEEN 1 AND 7",
            name=op.f("ck_staff_availability_day_of_week"),
        ),
        sa.CheckConstraint(
            "start_time < end_time",
            name=op.f("ck_staff_availability_time_order"),
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff_profiles.id"],
            name=op.f("fk_staff_availability_staff_id_staff_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staff_availability")),
    )
    op.create_index(
        op.f("ix_staff_availability_staff_id"), "staff_availability", ["staff_id"], unique=False
    )

    # ------------------------------------------------------------------
    # 8. staff_time_off
    # ------------------------------------------------------------------
    op.create_table(
        "staff_time_off",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_datetime", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        _ts_col("created_at"),
        _ts_col("updated_at"),
        sa.CheckConstraint(
            "start_datetime < end_datetime",
            name=op.f("ck_staff_time_off_datetime_order"),
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff_profiles.id"],
            name=op.f("fk_staff_time_off_staff_id_staff_profiles"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_staff_time_off")),
    )
    op.create_index(op.f("ix_staff_time_off_staff_id"), "staff_time_off", ["staff_id"], unique=False)

    # ------------------------------------------------------------------
    # 9. appointments
    # ------------------------------------------------------------------
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="scheduled"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.String(500), nullable=True),
        _ts_col("created_at"),
        _ts_col("updated_at"),
        sa.CheckConstraint(
            "scheduled_start < scheduled_end",
            name="ck_appointments_slot_order",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["client_profiles.id"],
            name=op.f("fk_appointments_client_id_client_profiles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name=op.f("fk_appointments_service_id_services"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff_profiles.id"],
            name=op.f("fk_appointments_staff_id_staff_profiles"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appointments")),
    )
    op.create_index(op.f("ix_appointments_client_id"), "appointments", ["client_id"], unique=False)
    op.create_index(op.f("ix_appointments_service_id"), "appointments", ["service_id"], unique=False)
    op.create_index(op.f("ix_appointments_staff_id"), "appointments", ["staff_id"], unique=False)
    op.create_index(op.f("ix_appointments_status"), "appointments", ["status"], unique=False)

    # ------------------------------------------------------------------
    # 10. appointment_events
    # ------------------------------------------------------------------
    op.create_table(
        "appointment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, default=uuid.uuid4),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name=op.f("fk_appointment_events_appointment_id_appointments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appointment_events")),
    )
    op.create_index(
        op.f("ix_appointment_events_appointment_id"),
        "appointment_events",
        ["appointment_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_index(
        op.f("ix_appointment_events_appointment_id"), table_name="appointment_events"
    )
    op.drop_table("appointment_events")

    op.drop_index(op.f("ix_appointments_status"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_staff_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_service_id"), table_name="appointments")
    op.drop_index(op.f("ix_appointments_client_id"), table_name="appointments")
    op.drop_table("appointments")

    op.drop_index(op.f("ix_staff_time_off_staff_id"), table_name="staff_time_off")
    op.drop_table("staff_time_off")

    op.drop_index(op.f("ix_staff_availability_staff_id"), table_name="staff_availability")
    op.drop_table("staff_availability")

    op.drop_index(op.f("ix_staff_services_staff_id"), table_name="staff_services")
    op.drop_index(op.f("ix_staff_services_service_id"), table_name="staff_services")
    op.drop_table("staff_services")

    op.drop_table("services")

    op.drop_index(op.f("ix_client_profiles_user_id"), table_name="client_profiles")
    op.drop_index(
        op.f("ix_client_profiles_preferred_staff_id"), table_name="client_profiles"
    )
    op.drop_table("client_profiles")

    op.drop_index(op.f("ix_staff_profiles_user_id"), table_name="staff_profiles")
    op.drop_table("staff_profiles")

    op.drop_index(op.f("ix_users_role_id"), table_name="users")
    op.drop_table("users")

    op.drop_table("roles")
