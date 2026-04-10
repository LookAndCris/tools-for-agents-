"""audit event columns

Revision ID: 002
Revises: 001
Create Date: 2026-04-09

Adds 6 typed nullable audit columns to appointment_events:
  - performed_by  (UUID)      — actor who triggered the event
  - old_start     (TIMESTAMPTZ) — slot start before reschedule
  - old_end       (TIMESTAMPTZ) — slot end before reschedule
  - new_start     (TIMESTAMPTZ) — slot start after reschedule
  - new_end       (TIMESTAMPTZ) — slot end after reschedule
  - reason        (VARCHAR 500) — cancellation reason

All columns are nullable for backward compatibility with existing rows.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "appointment_events",
        sa.Column(
            "performed_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.add_column(
        "appointment_events",
        sa.Column(
            "old_start",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "appointment_events",
        sa.Column(
            "old_end",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "appointment_events",
        sa.Column(
            "new_start",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "appointment_events",
        sa.Column(
            "new_end",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "appointment_events",
        sa.Column(
            "reason",
            sa.String(500),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("appointment_events", "reason")
    op.drop_column("appointment_events", "new_end")
    op.drop_column("appointment_events", "new_start")
    op.drop_column("appointment_events", "old_end")
    op.drop_column("appointment_events", "old_start")
    op.drop_column("appointment_events", "performed_by")
