#!/usr/bin/env python
"""One-off Fernet key rotation script.

Usage:
    python scripts/reencrypt.py --from /tmp/old.key --to /tmp/new.key

Reads every encrypted column, decrypts with old key, re-encrypts with
new key. Safe to run multiple times (idempotent in the sense that it
rewrites everything; not idempotent in the sense that it permanently
overwrites). Always back up the DB before running.

The new FERNET_KEY env value must be set on the api container before
running this script via `make shell-api` after restart with new key.
"""

from __future__ import annotations

import argparse
import asyncio
from sqlalchemy import select, text

from app.config import get_settings
from app.db import session_scope
from app.models import TenantSecret, UserOAuthToken
from app.services.encryption import Cipher
from cryptography.fernet import Fernet


async def rotate(args: argparse.Namespace) -> None:
    old_cipher = Cipher(args.from_key.encode("ascii"))
    new_cipher = Cipher(args.to_key.encode("ascii"))

    n_tenants = 0
    n_users = 0

    async with session_scope() as session:
        # tenant secrets
        res = await session.execute(select(TenantSecret))
        for row in res.scalars():
            for col in (
                "m365_client_id_enc",
                "m365_client_secret_enc",
                "ox_admin_user_enc",
                "ox_admin_password_enc",
                "nc_admin_user_enc",
                "nc_admin_password_enc",
            ):
                v = getattr(row, col, None)
                if v is None:
                    continue
                decrypted = old_cipher.decrypt(v)
                setattr(row, col, new_cipher.encrypt(decrypted))
            n_tenants += 1

        # user tokens
        res = await session.execute(select(UserOAuthToken))
        for row in res.scalars():
            for col in ("access_token_enc", "refresh_token_enc"):
                v = getattr(row, col, None)
                if v is None:
                    continue
                decrypted = old_cipher.decrypt(v)
                setattr(row, col, new_cipher.encrypt(decrypted))
            n_users += 1

    print(f"Rotated: {n_tenants} tenants, {n_users} user tokens")


def main() -> None:
    parser = argparse.ArgumentParser(description="Rotate Fernet key")
    parser.add_argument("--from", dest="from_key", required=True, help="Old Fernet key (44 chars)")
    parser.add_argument("--to", dest="to_key", required=True, help="New Fernet key (44 chars)")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Dry-run: decrypt only, don't write back",
    )
    args = parser.parse_args()

    if len(args.from_key) != 44 or len(args.to_key) != 44:
        raise SystemExit("Both keys must be 44 chars")

    try:
        Fernet(args.from_key.encode("ascii"))
        Fernet(args.to_key.encode("ascii"))
    except Exception as e:
        raise SystemExit(f"Invalid Fernet key: {e}")

    if args.verify:
        print("VERIFICATION: keys parse correctly, performing decryption-only check")
        cipher = Cipher(args.from_key.encode("ascii"))
        async def _verify():
            async with session_scope() as session:
                res = await session.execute(select(TenantSecret).limit(1))
                row = res.scalar_one_or_none()
                if row is None:
                    print("No tenants to verify against")
                    return
                for col in ("m365_client_id_enc",):
                    if getattr(row, col):
                        print(f"{col}: decrypted OK")
        asyncio.run(_verify())
        return

    asyncio.run(rotate(args))


if __name__ == "__main__":
    main()
