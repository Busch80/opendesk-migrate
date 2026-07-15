"""Unit tests for the Fernet cipher."""

from __future__ import annotations

import pytest

from app.services.encryption import Cipher, InvalidEncryptionKey, generate_fernet_key


def test_generate_fernet_key_returns_44_chars() -> None:
    key = generate_fernet_key()
    assert len(key) == 44
    assert isinstance(key, str)


def test_cipher_encrypt_decrypt_roundtrip() -> None:
    key = generate_fernet_key()
    cipher = Cipher(key.encode("ascii"))
    plaintext = "hello, world! äöü"
    ciphertext = cipher.encrypt(plaintext)
    assert ciphertext is not None
    assert ciphertext.startswith(b"odmig-v1\x00")
    assert plaintext == cipher.decrypt(ciphertext)


def test_cipher_encrypt_none() -> None:
    key = generate_fernet_key()
    cipher = Cipher(key.encode("ascii"))
    assert cipher.encrypt(None) is None
    assert cipher.decrypt(None) is None


def test_cipher_invalid_key_length() -> None:
    with pytest.raises(ValueError):
        Cipher(b"too-short")


def test_cipher_wrong_key_raises() -> None:
    cipher_a = Cipher(generate_fernet_key().encode("ascii"))
    cipher_b = Cipher(generate_fernet_key().encode("ascii"))

    ciphertext = cipher_a.encrypt("secret")
    with pytest.raises(InvalidEncryptionKey):
        cipher_b.decrypt(ciphertext)


def test_cipher_unknown_version_prefix() -> None:
    cipher = Cipher(generate_fernet_key().encode("ascii"))
    bogus = b"v999\\x00" + b"x" * 50
    with pytest.raises(InvalidEncryptionKey):
        cipher.decrypt(bogus)


def test_cipher_decrypt_optional_returns_none_on_error() -> None:
    cipher = Cipher(generate_fernet_key().encode("ascii"))
    bogus = b"odmig-v1\\x00" + b"garbage"
    assert cipher.decrypt_optional(bogus) is None
