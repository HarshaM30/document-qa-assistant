from __future__ import annotations

from pydantic import SecretStr

from docqa.auth.sessions import hash_token, new_token
from docqa.config import Settings


def test_tokens_are_random_and_long() -> None:
    tokens = {new_token() for _ in range(100)}
    assert len(tokens) == 100
    assert all(len(t) >= 40 for t in tokens)


def test_token_hash_depends_on_secret() -> None:
    a = Settings(session_secret_key=SecretStr("key-a"))
    b = Settings(session_secret_key=SecretStr("key-b"))
    assert hash_token("tok", a) == hash_token("tok", a)
    assert hash_token("tok", a) != hash_token("tok", b)
    assert len(hash_token("tok", a)) == 64
