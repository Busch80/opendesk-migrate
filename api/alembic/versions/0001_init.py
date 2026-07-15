"""Initial schema: tenants, users, OAuth tokens, jobs, errors, audit log.

Revision ID: 0001_init
Revises:
Create Date: 2026-07-15

"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID


revision: str = "0001_init"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")  # for gen_random_uuid()

    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(256), nullable=False),
        sa.Column("opendesk_base_url", sa.Text(), nullable=True),
        sa.Column("m365_tenant_id", sa.String(128), nullable=True),
        sa.Column("status", sa.Enum("active", "paused", "archived", name="tenant_status"), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tenants_code", "tenants", ["code"])

    op.create_table(
        "tenant_secrets",
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("m365_client_id_enc", sa.LargeBinary(), nullable=True),
        sa.Column("m365_client_secret_enc", sa.LargeBinary(), nullable=True),
        sa.Column("m365_redirect_uri", sa.Text(), nullable=True),
        sa.Column("ox_admin_url", sa.Text(), nullable=True),
        sa.Column("ox_admin_user_enc", sa.LargeBinary(), nullable=True),
        sa.Column("ox_admin_password_enc", sa.LargeBinary(), nullable=True),
        sa.Column("nc_admin_url", sa.Text(), nullable=True),
        sa.Column("nc_admin_user_enc", sa.LargeBinary(), nullable=True),
        sa.Column("nc_admin_password_enc", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "users_m365",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("m365_upn", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(512), nullable=True),
        sa.Column("mailbox_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("onedrive_used_bytes", sa.BigInteger(), nullable=True),
        sa.Column("mailbox_quota_bytes", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.Enum("pending", "active", "migrated", "error", "needs_reauth", name="user_status"), nullable=False, server_default="pending"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("tenant_id", "m365_upn", name="uq_users_m365_tenant_upn"),
    )
    op.create_index("ix_users_m365_tenant_id", "users_m365", ["tenant_id"])
    op.create_index("ix_users_m365_m365_upn", "users_m365", ["m365_upn"])

    op.create_table(
        "user_oauth_tokens",
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users_m365.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("access_token_enc", sa.LargeBinary(), nullable=True),
        sa.Column("refresh_token_enc", sa.LargeBinary(), nullable=True),
        sa.Column("scopes", ARRAY(sa.String()), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mail_delta_link", sa.Text(), nullable=True),
        sa.Column("calendar_delta_link", sa.Text(), nullable=True),
        sa.Column("contacts_delta_link", sa.Text(), nullable=True),
        sa.Column("onedrive_delta_link", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "migration_jobs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users_m365.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_type", sa.Enum("mail", "calendar", "contacts", "onedrive", name="job_type"), nullable=False),
        sa.Column("phase", sa.Enum("discovery", "full", "delta", "verify", "complete", "failed", "cancelled", name="job_phase"), nullable=False, server_default="discovery"),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resumable_state", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_migration_jobs_tenant_id", "migration_jobs", ["tenant_id"])
    op.create_index("ix_migration_jobs_user_id", "migration_jobs", ["user_id"])
    op.create_index("ix_migration_jobs_job_type", "migration_jobs", ["job_type"])

    op.create_table(
        "errors",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("job_id", UUID(as_uuid=False), nullable=True),
        sa.Column("job_type", sa.Enum("mail", "calendar", "contacts", "onedrive", name="job_type", create_type=False), nullable=True),
        sa.Column("item_id", sa.Text(), nullable=True),
        sa.Column("item_hash_sha256", sa.String(64), nullable=True),
        sa.Column("error_type", sa.String(128), nullable=False),
        sa.Column("error_msg", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_errors_job_id", "errors", ["job_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", UUID(as_uuid=False), nullable=True),
        sa.Column("actor", sa.String(256), nullable=True),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("target", sa.Text(), nullable=True),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ip", INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])

    # Make audit_log append-only — DEL/UPD blocked except via SECURITY DEFINER function.
    op.execute(
        "REVOKE ALL ON audit_log FROM PUBLIC"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_log_no_modify() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER audit_log_no_update BEFORE UPDATE ON audit_log FOR EACH ROW "
        "EXECUTE FUNCTION audit_log_no_modify();"
    )
    op.execute(
        "CREATE TRIGGER audit_log_no_delete BEFORE DELETE ON audit_log FOR EACH ROW "
        "EXECUTE FUNCTION audit_log_no_modify();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_delete ON audit_log")
    op.execute("DROP TRIGGER IF EXISTS audit_log_no_update ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_no_modify()")
    op.drop_table("audit_log")
    op.drop_table("errors")
    op.drop_table("migration_jobs")
    op.drop_table("user_oauth_tokens")
    op.drop_table("users_m365")
    op.drop_table("tenant_secrets")
    op.drop_table("tenants")
    sa.Enum(name="job_phase").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="job_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="tenant_status").drop(op.get_bind(), checkfirst=True)
