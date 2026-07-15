"""Seed a demo tenant + users for local exploration.

Run via:
    docker compose exec api python -m scripts.seed_demo
"""

from __future__ import annotations

import asyncio
import secrets

from sqlalchemy import select

from app.db import session_scope
from app.models import AuditLog, Tenant, TenantSecret, TenantStatus, UserM365, UserStatus
from app.services.encryption import get_cipher


async def main() -> None:
    cipher = get_cipher()

    async with session_scope() as session:
        # Skip if already seeded
        res = await session.execute(select(Tenant).where(Tenant.code == "demo"))
        if res.scalar_one_or_none() is not None:
            print("Demo tenant already exists. Skipping.")
            return

        tenant = Tenant(
            code="demo",
            display_name="Demo Org AG",
            opendesk_base_url="https://ox.demo.local",
            m365_tenant_id="00000000-0000-0000-0000-000000000000",
            status=TenantStatus.ACTIVE,
        )
        session.add(tenant)
        await session.flush()

        session.add(
            TenantSecret(
                tenant_id=tenant.id,
                m365_client_id_enc=cipher.encrypt("00000000-0000-0000-0000-000000000000"),
                m365_client_secret_enc=cipher.encrypt(secrets.token_urlsafe(32)),
                m365_redirect_uri="http://localhost:8080/oauth/callback",
                ox_admin_url="https://ox.demo.local",
                ox_admin_user_enc=cipher.encrypt("oxadmin"),
                ox_admin_password_enc=cipher.encrypt("changeme"),
                nc_admin_url="https://nc.demo.local",
                nc_admin_user_enc=cipher.encrypt("admin"),
                nc_admin_password_enc=cipher.encrypt("changeme"),
            )
        )

        for i in range(1, 6):
            user = UserM365(
                tenant_id=tenant.id,
                m365_upn=f"user{i}@demo.local",
                display_name=f"Demo User {i}",
                status=UserStatus.PENDING,
            )
            session.add(user)

        session.add(
            AuditLog(
                tenant_id=tenant.id,
                actor="seed",
                action="tenant.seed",
                target="demo",
                payload={"users": 5},
            )
        )

    print("Seeded 'demo' tenant with 5 users.")


if __name__ == "__main__":
    asyncio.run(main())
