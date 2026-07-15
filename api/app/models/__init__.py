"""Domain models — SQLAlchemy 2.0 declarative.

Schema reflects the multi-tenant m365 → openDesk migration store.
Sensitive columns (secrets, tokens) are bytea; Fernet-encrypted at the application layer.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BIGINT,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base."""

    type_annotation_map = {
        dict[str, Any]: JSONB,
        list[str]: ARRAY(String),
    }


# Enums -----------------------------------------------------------------------


class TenantStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    MIGRATED = "migrated"
    ERROR = "error"
    NEEDS_REAUTH = "needs_reauth"


class JobPhase(str, enum.Enum):
    DISCOVERY = "discovery"
    FULL = "full"
    DELTA = "delta"
    VERIFY = "verify"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, enum.Enum):
    MAIL = "mail"
    CALENDAR = "calendar"
    CONTACTS = "contacts"
    ONEDRIVE = "onedrive"


# Tables ----------------------------------------------------------------------


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    opendesk_base_url: Mapped[str | None] = mapped_column(Text)
    m365_tenant_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[TenantStatus] = mapped_column(Enum(TenantStatus, name="tenant_status"), default=TenantStatus.ACTIVE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    secrets: Mapped[TenantSecret | None] = relationship("TenantSecret", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    users: Mapped[list[UserM365]] = relationship("UserM365", back_populates="tenant", cascade="all, delete-orphan")
    jobs: Mapped[list[MigrationJob]] = relationship("MigrationJob", back_populates="tenant", cascade="all, delete-orphan")


class TenantSecret(Base):
    """Per-tenant encrypted secrets.

    All *_enc columns are Fernet ciphertext (Fernet-encrypted application-side).
    """

    __tablename__ = "tenant_secrets"

    tenant_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    m365_client_id_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    m365_client_secret_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    m365_redirect_uri: Mapped[str | None] = mapped_column(Text)
    ox_admin_url: Mapped[str | None] = mapped_column(Text)
    ox_admin_user_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    ox_admin_password_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    nc_admin_url: Mapped[str | None] = mapped_column(Text)
    nc_admin_user_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    nc_admin_password_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="secrets")


class UserM365(Base):
    __tablename__ = "users_m365"
    __table_args__ = (UniqueConstraint("tenant_id", "m365_upn", name="uq_users_m365_tenant_upn"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    m365_upn: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(512))
    mailbox_size_bytes: Mapped[int | None] = mapped_column(BIGINT)
    onedrive_used_bytes: Mapped[int | None] = mapped_column(BIGINT)
    mailbox_quota_bytes: Mapped[int | None] = mapped_column(BIGINT)
    status: Mapped[UserStatus] = mapped_column(Enum(UserStatus, name="user_status"), default=UserStatus.PENDING)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="users")
    oauth_tokens: Mapped[UserOAuthToken | None] = relationship(
        "UserOAuthToken", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    jobs: Mapped[list[MigrationJob]] = relationship("MigrationJob", back_populates="user", cascade="all, delete-orphan")


class UserOAuthToken(Base):
    """Per-user M365 OAuth tokens.

    The refresh_token is the long-lived credential. Access tokens are
    short-lived and refreshed automatically by a periodic Celery beat job.
    """

    __tablename__ = "user_oauth_tokens"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users_m365.id", ondelete="CASCADE"), primary_key=True
    )
    access_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    refresh_token_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    mail_delta_link: Mapped[str | None] = mapped_column(Text)
    calendar_delta_link: Mapped[str | None] = mapped_column(Text)
    contacts_delta_link: Mapped[str | None] = mapped_column(Text)
    onedrive_delta_link: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[UserM365] = relationship("UserM365", back_populates="oauth_tokens")


class MigrationJob(Base):
    __tablename__ = "migration_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users_m365.id", ondelete="CASCADE"), index=True)
    job_type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type"), nullable=False, index=True)
    phase: Mapped[JobPhase] = mapped_column(Enum(JobPhase, name="job_phase"), default=JobPhase.DISCOVERY)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[int] = mapped_column(Integer, default=0)
    resumable_state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="jobs")
    user: Mapped[UserM365] = relationship("UserM365", back_populates="jobs")


class Error(Base):
    __tablename__ = "errors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), index=True)
    job_type: Mapped[JobType | None] = mapped_column(Enum(JobType, name="job_type", create_type=False))
    item_id: Mapped[str | None] = mapped_column(Text)
    item_hash_sha256: Mapped[str | None] = mapped_column(String(64))  # never store content
    error_type: Mapped[str] = mapped_column(String(128))
    error_msg: Mapped[str] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """Append-only audit log.

    DELETE/UPDATE are revoked at DB level in a separate migration.
    """

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), index=True)
    actor: Mapped[str | None] = mapped_column(String(256))
    action: Mapped[str] = mapped_column(String(128), index=True)
    target: Mapped[str | None] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


__all__ = [
    "Base",
    "Tenant",
    "TenantSecret",
    "TenantStatus",
    "UserM365",
    "UserStatus",
    "UserOAuthToken",
    "MigrationJob",
    "JobPhase",
    "JobType",
    "Error",
    "AuditLog",
]
