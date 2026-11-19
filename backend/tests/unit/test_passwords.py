from __future__ import annotations

import asyncio

from docqa.auth.passwords import (
    hash_password,
    hash_password_async,
    needs_rehash,
    verify_dummy_async,
    verify_password,
    verify_password_async,
)


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


async def test_async_helpers_match_the_sync_ones() -> None:
    hashed = await hash_password_async("s3cret-password")
    assert await verify_password_async(hashed, "s3cret-password")
    assert not await verify_password_async(hashed, "wrong")
    await verify_dummy_async("anything")


async def test_hashing_does_not_block_the_event_loop() -> None:
    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.005)
            ticks += 1

    task = asyncio.create_task(ticker())
    await asyncio.gather(*(hash_password_async(f"password-{i}") for i in range(4)))
    task.cancel()
    assert ticks >= 3  # the loop kept running while four argon2 hashes were computed
