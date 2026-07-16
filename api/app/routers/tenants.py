"""Tenant management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session_dep
from app.logging import get_logger
from app.models import AuditLog, Tenant, TenantStatus
from app.schemas import SecretsRotate, TenantCreate, TenantRead, TenantUpdate
from app.services.encryption import get_cipher

router = APIRouter()
logger = get_logger(__name__)


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate,
    session: AsyncSession = Depends(db_session_dep),
) -> TenantRead:
    """Create a new tenant with encrypted secrets."""
    cipher = get_cipher()

    tenant = Tenant(
        code=payload.code,
        display_name=payload.display_name,
        opendesk_base_url=payload.opendesk_base_url,
        m365_tenant_id=payload.m365_tenant_id,
        status=TenantStatus.ACTIVE,
    )
    session.add(tenant)
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"Tenant code already exists: {payload.code}") from e

    from app.models import TenantSecret

    secrets = TenantSecret(
        tenant_id=tenant.id,
        m365_client_id_enc=cipher.encrypt(payload.m365_client_id) if payload.m365_client_id else None,
        m365_client_secret_enc=cipher.encrypt(payload.m365_client_secret) if payload.m365_client_secret else None,
        m365_redirect_uri=payload.m365_redirect_uri,
        ox_admin_url=payload.ox_admin_url,
        ox_admin_user_enc=cipher.encrypt(payload.ox_admin_user) if payload.ox_admin_user else None,
        ox_admin_password_enc=cipher.encrypt(payload.ox_admin_password) if payload.ox_admin_password else None,
        nc_admin_url=payload.nc_admin_url,
        nc_admin_user_enc=cipher.encrypt(payload.nc_admin_user) if payload.nc_admin_user else None,
        nc_admin_password_enc=cipher.encrypt(payload.nc_admin_password) if payload.nc_admin_password else None,
    )
    session.add(secrets)

    session.add(
        AuditLog(
            tenant_id=tenant.id,
            actor="system",
            action="tenant.create",
            target=tenant.code,
            payload={"display_name": payload.display_name},
        )
    )

    await session.commit()
    await session.refresh(tenant)
    logger.info("tenant_created", tenant_id=str(tenant.id), code=tenant.code)
    return TenantRead.model_validate(tenant)


@router.get("", response_model=list[TenantRead])
async def list_tenants(
    session: AsyncSession = Depends(db_session_dep),
) -> list[TenantRead]:
    res = await session.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return [TenantRead.model_validate(t) for t in res.scalars()]


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenant(tenant_id: UUID, session: AsyncSession = Depends(db_session_dep)) -> TenantRead:
    res = await session.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    tenant = res.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    return TenantRead.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantRead)
async def update_tenant(
    tenant_id: UUID, payload: TenantUpdate, session: AsyncSession = Depends(db_session_dep)
) -> TenantRead:
    res = await session.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    tenant = res.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    if payload.display_name is not None:
        tenant.display_name = payload.display_name
    if payload.opendesk_base_url is not None:
        tenant.opendesk_base_url = payload.opendesk_base_url
    if payload.m365_tenant_id is not None:
        tenant.m365_tenant_id = payload.m365_tenant_id
    if payload.status is not None:
        tenant.status = payload.status
    session.add(AuditLog(tenant_id=str(tenant_id), actor="system", action="tenant.update", target=payload.model_dump_json()))
    await session.commit()
    await session.refresh(tenant)
    return TenantRead.model_validate(tenant)


@router.post("/{tenant_id}/rotate-secrets", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def rotate_secrets(tenant_id: UUID, payload: SecretsRotate, session: AsyncSession = Depends(db_session_dep)) -> None:
    """Re-encrypt specific secrets with the same Fernet key.

    Audit-logged and rotated_at is bumped.
    """
    cipher = get_cipher()
    from app.models import TenantSecret

    res = await session.execute(select(TenantSecret).where(TenantSecret.tenant_id == str(tenant_id)))
    secrets = res.scalar_one_or_none()
    if secrets is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant has no secrets row")
    if payload.m365_client_id is not None:
        secrets.m365_client_id_enc = cipher.encrypt(payload.m365_client_id)
    if payload.m365_client_secret is not None:
        secrets.m365_client_secret_enc = cipher.encrypt(payload.m365_client_secret)
    if payload.ox_admin_user is not None:
        secrets.ox_admin_user_enc = cipher.encrypt(payload.ox_admin_user)
    if payload.ox_admin_password is not None:
        secrets.ox_admin_password_enc = cipher.encrypt(payload.ox_admin_password)
    if payload.nc_admin_user is not None:
        secrets.nc_admin_user_enc = cipher.encrypt(payload.nc_admin_user)
    if payload.nc_admin_password is not None:
        secrets.nc_admin_password_enc = cipher.encrypt(payload.nc_admin_password)

    from datetime import datetime, timezone

    secrets.rotated_at = datetime.now(tz=timezone.utc)
    session.add(AuditLog(tenant_id=str(tenant_id), actor="system", action="secrets.rotate", target=str(tenant_id)))
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
