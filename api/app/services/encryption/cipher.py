"""Fernet-based encryption for sensitive columns.

Used for tenant-secrets and per-user OAuth tokens stored as bytea in Postgres.
Fernet key (44 chars, base64-url) comes from FERNET_KEY env var.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from typing import Final

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings
from app.logging import get_logger

logger = get_logger(__name__)

__all__ = ["Cipher", "InvalidEncryptionKey", "generate_fernet_key"]

_VERSION: Final[bytes] = b"odmig-v1\x00"


class InvalidEncryptionKey(Exception):
    """Raised when ciphertext cannot be decrypted (wrong key, corrupt data)."""


class Cipher:
    """Symmetric encryption/decryption using Fernet (AES-128-CBC + HMAC)."""

    __slots__ = ("_fernet",)

    def __init__(self, key: bytes) -> None:
        if len(key) != 44:
            raise ValueError(f"Fernet key must be 44 chars (base64), got {len(key)}")
        try:
            self._fernet = Fernet(key)
        except (ValueError, TypeError) as e:
            raise InvalidEncryptionKey(f"Invalid Fernet key: {e}") from e

    def encrypt(self, plaintext: str | bytes | None) -> bytes | None:
        """Encrypt a plaintext value. Returns None if input is None."""
        if plaintext is None:
            return None
        if isinstance(plaintext, str):
            data = plaintext.encode("utf-8")
        else:
            data = plaintext
        token = self._fernet.encrypt(data)
        return _VERSION + token

    def decrypt(self, ciphertext: bytes | None) -> str | None:
        """Decrypt ciphertext. Returns None if input is None."""
        if ciphertext is None:
            return None
        if not ciphertext.startswith(_VERSION):
            raise InvalidEncryptionKey("Ciphertext has unknown version prefix")
        token = ciphertext[len(_VERSION):]
        try:
            plaintext = self._fernet.decrypt(token)
        except InvalidToken as e:
            raise InvalidEncryptionKey("Unable to decrypt — wrong key or corrupt data") from e
        return plaintext.decode("utf-8")

    def decrypt_optional(self, ciphertext: bytes | None) -> str | None:
        """Decrypt but return None on error instead of raising (for migrations)."""
        try:
            return self.decrypt(ciphertext)
        except InvalidEncryptionKey:
            return None


@lru_cache(maxsize=1)
def get_cipher() -> Cipher:
    """Get a process-local cipher instance."""
    settings = get_settings()
    return Cipher(settings.fernet_key_bytes)


def generate_fernet_key() -> str:
    """Generate a fresh 44-char Fernet key (base64-url encoded).

    Returns 44 ASCII characters. Use as FERNET_KEY env value.
    Suitable to be called once during bootstrap.
    """
    return Fernet.generate_key().decode("ascii")


def rotate_key_helper() -> bytes:
    """Generate a strong token for use as SECRET_KEY."""
    return secrets.token_urlsafe(64).encode("ascii")
