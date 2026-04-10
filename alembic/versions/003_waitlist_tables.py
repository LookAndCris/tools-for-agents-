"""waitlist tables

Revision ID: 003
Revises: 002
Create Date: 2026-04-09

Creates two new tables:
  - waitlist        — one row per client/service waitlist entry
  - waitlist_notifications — audit record created when a waitlist entry is notified

Schema:
  waitlist (
    id               UUID PK
    client_id        UUID FK → client_profiles(id) RESTRICT
    service_id       UUID FK → services(id) RESTRICT
    preferred_staff_id UUID FK → staff_profiles(id) SET NULL, nullable
    preferred_start  TIMESTAMPTZ nullable
    preferred_end    TIMESTAMPTZ nullable
    status           VARCHAR(20) NOT NULL default 'pending'
    notes            TEXT nullable
    created_at       TIMESTAMPTZ NOT NULL
    updated_at       TIMESTAMPTZ NOT NULL
  )

  waitlist_notifications (
    id               UUID PK
    waitlist_id      UUID FK → waitlist(id) CASCADE
    appointment_id   UUID FK → appointments(id) SET NULL, nullable
    notified_at      TIMESTAMPTZ NOT NULL
    expires_at       TIMESTAMPTZ nullable
    created_at       TIMESTAMPTZ NOT NULL
    updated_at       TIMESTAMPTZ NOT NULL
  )

Indexes:
  - waitlist(client_id)
  - waitlist(service_id)
  - waitlist(preferred_staff_id)
  - waitlist(status)
  - waitlist_notifications(waitlist_id)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # waitlist
    # ------------------------------------------------------------------
    op.create_table(
        "waitlist",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("preferred_staff_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("preferred_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferred_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["client_profiles.id"],
            name="fk_waitlist_client_id_client_profiles",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["service_id"],
            ["services.id"],
            name="fk_waitlist_service_id_services",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["preferred_staff_id"],
            ["staff_profiles.id"],
            name="fk_waitlist_preferred_staff_id_staff_profiles",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_waitlist"),
    )
    op.create_index("ix_waitlist_client_id", "waitlist", ["client_id"])
    op.create_index("ix_waitlist_service_id", "waitlist", ["service_id"])
    op.create_index("ix_waitlist_preferred_staff_id", "waitlist", ["preferred_staff_id"])
    op.create_index("ix_waitlist_status", "waitlist", ["status"])

    # ------------------------------------------------------------------
    # waitlist_notifications
    # ------------------------------------------------------------------
    op.create_table(
        "waitlist_notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("waitlist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["waitlist_id"],
            ["waitlist.id"],
            name="fk_waitlist_notifications_waitlist_id_waitlist",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name="fk_waitlist_notifications_appointment_id_appointments",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_waitlist_notifications"),
    )
    op.create_index(
        "ix_waitlist_notifications_waitlist_id",
        "waitlist_notifications",
        ["waitlist_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_waitlist_notifications_waitlist_id", table_name="waitlist_notifications")
    op.drop_table("waitlist_notifications")

    op.drop_index("ix_waitlist_status", table_name="waitlist")
    op.drop_index("ix_waitlist_preferred_staff_id", table_name="waitlist")
    op.drop_index("ix_waitlist_service_id", table_name="waitlist")
    op.drop_index("ix_waitlist_client_id", table_name="waitlist")
    op.drop_table("waitlist")
