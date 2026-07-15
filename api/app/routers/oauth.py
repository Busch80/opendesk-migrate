"""OAuth flow routes — Device Code flow for M365 delegated permissions.

The frontend triggers a device-code flow for each user. The user visits
https://microsoft.com/devicelogin, enters the user_code, and grants
Mail.Read etc. The backend polls MSAL and stores the resulting tokens.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import db_session_dep
from app.logging import get_logger
from app.models import AuditLog, UserM365, UserOAuthToken
from app.schemas import DeviceCodeResponse, DeviceCodeStart, OAuthStatus
from app.services.encryption import get_cipher

router = APIRouter()
logger = get_logger(__name__)


@router.post("/device-code", response_model=DeviceCodeResponse)
async def start_device_code(
    payload: DeviceCodeStart,
    session: AsyncSession = Depends(db_session_dep),
) -> DeviceCodeResponse:
    """Initiate a Microsoft device-code flow for the given user.

    Stores the device_code in the UserOAuthToken row so we can poll on
    the callback endpoint.
    """
    cipher = get_cipher()

    res = await session.execute(
        select(UserM365).where(UserM365.id == str(payload.user_id))
    )
    user = res.scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    # We need the tenant secret (client_id/secret) which is sent via header for this endpoint
    # OR fetched via the user's tenant_id. For now, raise until creds are wired:
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "OAuth device-code requires real M365 client_id/secret. "
        "Set up a real M365 sandbox tenant first, then this endpoint will return "
        "an HTTP 200 with user_code/verification_uri.",
    )

    # Pseudo flow:
    #
    # 1. Decrypt tenant's m365_client_id and client_secret
    # 2. Build MSAL PublicClientApplication with client_id
    # 3. scopes = payload.scopes or default scopes
    # 4. flow = app.initiate_device_flow(scopes)
    # 5. Return DeviceCodeResponse(user_code=flow['user_code'], device_code=flow['device_code'],
    #                              verification_uri=flow['verification_uri'], ... )
    # 6. Persist flow['device_code'] + flow['expires_at'] + flow['interval']
    # 7. The user (or frontend) calls /oauth/callback with the device_code
    #    which we poll, exchange, persist refresh_token, then mark user status ACTIVE.


@router.get("/status/{user_id}", response_model=OAuthStatus)
async def oauth_status(
    user_id: UUID, session: AsyncSession = Depends(db_session_dep)
) -> OAuthStatus:
    res = await session.execute(
        select(UserOAuthToken).where(UserOAuthToken.user_id == str(user_id))
    )
    token = res.scalar_one_or_none()
    if token is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No OAuth token for this user yet")
    return OAuthStatus.model_validate(token)


@router.post("/callback/{user_id}")
async def oauth_callback(
    user_id: UUID, session: AsyncSession = Depends(db_session_dep)
) -> dict[str, str]:
    """Poll MSAL for the device-code result and persist tokens.

    Called repeatedly by frontend after the user enters user_code at
    https://microsoft.com/devicelogin.
    """
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "OAuth callback needs MSAL client + sandbox M365 tenant credentials.",
    )


__all__ = ["router"]
