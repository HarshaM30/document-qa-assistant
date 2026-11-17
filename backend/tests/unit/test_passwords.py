from __future__ import annotations

from docqa.auth.passwords import hash_password, needs_rehash, verify_password


def test_hash_is_argon2id_and_verifies() -> None:
    hashed = hash_password("s3cret-pass")
    assert hashed.startswith("$argon2id$")
    assert verify_password(hashed, "s3cret-pass")
    assert not verify_password(hashed, "wrong")
    assert not needs_rehash(hashed)


def test_hashes_are_salted() -> None:
    assert hash_password("same") != hash_password("same")


def test_malformed_hash_does_not_raise() -> None:
    assert not verify_password("not-a-hash", "anything")
