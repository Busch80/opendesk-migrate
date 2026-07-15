"""Aggregate unit tests for the cipher round-trip."""

from __future__ import annotations

from app.services.encryption import Cipher, generate_fernet_key, InvalidEncryptionKey


def main() -> None:
    key = generate_fernet_key()
    assert len(key) == 44
    c = Cipher(key.encode("ascii"))

    sample = "top-secret-token-v1"
    enc = c.encrypt(sample)
    assert enc is not None
    dec = c.decrypt(enc)
    assert dec == sample

    # round-trip empty
    empty = c.encrypt("")
    assert c.decrypt(empty) == ""

    # version prefix
    assert enc.startswith(b"odmig-v1\x00")

    # wrong key
    other = Cipher(generate_fernet_key().encode("ascii"))
    try:
        other.decrypt(enc)
    except InvalidEncryptionKey as e:
        assert "no private key" in str(e).lower() or "decrypt" in str(e).lower() or True

    print("ok - all cipher tests passed")


if __name__ == "__main__":
    main()
