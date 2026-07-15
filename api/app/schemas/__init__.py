"""Pydantic schemas for API payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import JobPhase, JobType, TenantStatus, UserStatus


# Shared -----------------------------------------------------------------------


class ORMDict(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Tenants ----------------------------------------------------------------------


class TenantCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_-]+$")
    display_name: str = Field(min_length=1, max_length=256)
    opendesk_base_url: str | None = None
    m365_tenant_id: str | None = None
    m365_client_id: str | None = None
    m365_client_secret: str | None = None
    m365_redirect_uri: str | None = None
    ox_admin_url: str | None = None
    ox_admin_user: str | None = None
    ox_admin_password: str | None = None
    nc_admin_url: str | None = None
    nc_admin_user: str | None = None
    nc_admin_password: str | None = None


class TenantUpdate(BaseModel):
    display_name: str | None = None
    opendesk_base_url: str | None = None
    m365_tenant_id: str | None = None
    status: TenantStatus | None = None


class TenantRead(ORMDict):
    id: UUID
    code: str
    display_name: str
    opendesk_base_url: str | None
    m365_tenant_id: str | None
    status: TenantStatus
    created_at: datetime
    updated_at: datetime


class SecretsRotate(BaseModel):
    m365_client_id: str | None = None
    m365_client_secret: str | None = None
    ox_admin_user: str | None = None
    ox_admin_password: str | None = None
    nc_admin_user: str | None = None
    nc_admin_password: str | None = None


# Users ------------------------------------------------------------------------


class UserCreate(BaseModel):
    m365_upn: EmailStr
    display_name: str | None = None


class UsersBulkImport(BaseModel):
    items: list[UserCreate] = Field(min_length=1, max_length=1000)


class UserRead(ORMDict):
    id: UUID
    tenant_id: UUID
    m365_upn: str
    display_name: str | None
    mailbox_size_bytes: int | None
    onedrive_used_bytes: int | None
    mailbox_quota_bytes: int | None
    status: UserStatus
    last_synced_at: datetime | None


# OAuth ------------------------------------------------------------------------


class DeviceCodeStart(BaseModel):
    user_id: UUID
    scopes: list[str] | None = None


class DeviceCodeResponse(BaseModel):
    user_code: str
    device_code: str
    verification_uri: str
    expires_in: int
    interval: int
    message: str


class OAuthCallback(BaseModel):
    code: str
    state: str | None = None


class OAuthStatus(ORMDict):
    user_id: UUID
    scopes: list[str]
    expires_at: datetime | None


# Jobs -------------------------------------------------------------------------


class JobStart(BaseModel):
    user_id: UUID
    job_type: JobType
    phase: JobPhase = JobPhase.DISCOVERY
    dry_run: bool = False


class JobRead(ORMDict):
    id: UUID
    tenant_id: UUID
    user_id: UUID
    job_type: JobType
    phase: JobPhase
    total_items: int
    processed: int
    errors: int
    last_error: str | None
    resumable_state: dict[str, Any]
    started_at: datetime | None
    finished_at: datetime | None


class JobRetry(BaseModel):
    pass


# Errors -----------------------------------------------------------------------


class ErrorRead(ORMDict):
    id: int
    job_id: UUID | None
    job_type: JobType | None
    item_id: str | None
    error_type: str
    error_msg: str
    retry_count: int
    resolved: bool
    created_at: datetime


# Reconciliation / reports -----------------------------------------------------


class ReconciliationRow(BaseModel):
    user_id: UUID
    m365_upn: str
    domain: str  # mail | calendar | contacts | onedrive
    expected_count: int
    actual_count: int
    missing_ids: list[str]


# Health -----------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    database: str
    redis: str | None = None
    storage: dict[str, Any] | None = None
