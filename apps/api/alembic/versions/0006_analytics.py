"""analytics: raw events, users, daily rollup

Revision ID: 0006_analytics
Revises: 0005_breakout_events
Create Date: 2026-09-20 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006_analytics"
down_revision = "0005_breakout_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Raw, append-only event log: the auditable source of truth for every metric.
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        # ts is the SERVER receive time (authoritative); client_ts is the device clock, kept for reference.
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("client_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("visitor_id", sa.String(40), nullable=False),
        sa.Column("session_id", sa.String(40), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("path", sa.String(300), nullable=True),
        sa.Column("props", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("referrer", sa.String(300), nullable=True),
        sa.Column("utm_source", sa.String(100), nullable=True),
        sa.Column("utm_medium", sa.String(100), nullable=True),
        sa.Column("utm_campaign", sa.String(100), nullable=True),
        sa.Column("device", sa.String(12), nullable=True),
        sa.Column("browser", sa.String(30), nullable=True),
        sa.Column("os", sa.String(30), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("viewport_w", sa.SmallInteger, nullable=True),
        sa.Column("is_bot", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("app_version", sa.String(40), nullable=True),
    )
    op.create_index("ix_analytics_events_ts", "analytics_events", ["ts"])
    op.create_index("ix_analytics_events_event_ts", "analytics_events", ["event", "ts"])
    op.create_index("ix_analytics_events_visitor_ts", "analytics_events", ["visitor_id", "ts"])
    op.create_index("ix_analytics_events_session", "analytics_events", ["session_id"])

    # One row per signed-in user (opaque id only, no email) so first-seen survives raw-event pruning.
    op.create_table(
        "analytics_users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_count", sa.BigInteger, nullable=False, server_default=sa.text("0")),
    )

    # Permanent, tiny per-day totals: history that outlives raw-event retention.
    op.create_table(
        "analytics_daily",
        sa.Column("day", sa.Date, primary_key=True),
        sa.Column("visitors", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("new_visitors", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("returning_visitors", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("sessions", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("pageviews", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("clicks", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("events", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("signed_in_users", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("new_users", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("bounced_sessions", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("avg_session_seconds", sa.Numeric(10, 1), nullable=False, server_default=sa.text("0")),
        sa.Column("scans_run", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("errors", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("analytics_daily")
    op.drop_table("analytics_users")
    op.drop_index("ix_analytics_events_session", table_name="analytics_events")
    op.drop_index("ix_analytics_events_visitor_ts", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_ts", table_name="analytics_events")
    op.drop_index("ix_analytics_events_ts", table_name="analytics_events")
    op.drop_table("analytics_events")
