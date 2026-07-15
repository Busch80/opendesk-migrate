"""Per-user (M365 enduser) management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session_dep
from app.models import AuditLog, Tenant, UserM365, UserStatus
from app.schemas import UserCreate, UserRead, UsersBulkImport
from app.logging import get_logger

router = APIRouter(prefix="/tenants/{tenant_id}/users", tags=["users"])
logger = get_logger(__name__)


async def _get_tenant(session: AsyncSession, tenant_id: UUID) -> Tenant:
    res = await session.execute(select(Tenant).where(Tenant.id == str(tenant_id)))
    t = res.scalar_one_or_none()
    if t is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    return t


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    tenant_id: UUID, payload: UserCreate, session: AsyncSession = Depends(db_session_dep)
) -> UserRead:
    await _get_tenant(session, tenant_id)
    user = UserM365(
        tenant_id=str(tenant_id),
        m365_upn=str(payload.m365_upn),
        display_name=payload.display_name,
        status=UserStatus.PENDING,
    )
    session.add(user)
    session.add(AuditLog(tenant_id=str(tenant_id), actor="system", action="user.create", target=user.m365_upn))
    await session.commit()
    await session.refresh(user)
    return UserRead.model_validate(user)


@router.post("/bulk", response_model=list[UserRead], status_code=status.HTTP_201_CREATED)
async def bulk_import_users(
    tenant_id: UUID,
    payload: UsersBulkImport,
    session: AsyncSession = Depends(db_session_dep),
) -> list[UserRead]:
    await _get_tenant(session, tenant_id)
    users = [
        UserM365(
            tenant_id=str(tenant_id),
            m365_upn=str(item.m365_upn),
            display_name=item.display_name,
            status=UserStatus.PENDING,
        )
        for item in payload.items
    ]
    session.add_all(users)
    session.add(AuditLog(tenant_id=str(tenant_id), actor="system", action="user.bulk_import", target=f"{len(users)} users"))
    await session.commit()
    for u in users:
        await session.refresh(u)
    return [UserRead.model_validate(u) for u in users]


@router.get("", response_model=list[UserRead])
async def list_users(
    tenant_id: UUID,
    session: AsyncSession = Depends(db_session_dep),
    status_filter: UserStatus | None = None,
) -> list[UserRead]:
    await _get_tenant(session, tenant_id)
    stmt = select(UserM365).where(UserM365.tenant_id == str(tenant_id)).order_by(UserM365.m365_upn)
    if status_filter is not None:
        stmt = stmt.where(UserM365.status == status_filter)
    res = await session.execute(stmt)
    return [UserRead.model_validate(u) for u in res.scalars()]


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    tenant_id: UUID, user_id: UUID, session: AsyncSession = Depends(db_session_dep)
) -> UserRead:
    res = await session.execute(
        select(UserM365).where(UserM365.id == str(user_id), UserM365.tenant_id == str(tenant_id))
    )
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    tenant_id: UUID, user_id: UUID, session: AsyncSession = Depends(db_session_dep)
) -> None:
    res = await session.execute(
        select(UserM365).where(UserM365.id == str(user_id), UserM365.tenant_id == str(tenant_id))
    )
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await session.delete(user)
    session.add(AuditLog(tenant_id=str(tenant_id), actor="system", action="user.delete", target=user.m365_upn))
    await session.commit()
