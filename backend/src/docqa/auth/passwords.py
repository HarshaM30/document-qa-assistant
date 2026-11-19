"""Password hashing with argon2id."""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# argon2-cffi defaults follow RFC 9106's low-memory profile (argon2id, 64 MiB, t=3, p=4).
_hasher = PasswordHasher()

# Verified against when the email is unknown, so login timing doesn't reveal which emails exist.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing-equalization")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_dummy(password: str) -> None:
    verify_password(_DUMMY_HASH, password)


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# Each hash or verify takes tens of milliseconds of CPU and 64 MiB of memory. The async
# versions run it in a thread (argon2 releases the GIL), so a login doesn't stall every
# other request on the event loop, and cap how many run at once to bound memory.
MAX_CONCURRENT_HASHES = 4
_hash_slots = asyncio.Semaphore(MAX_CONCURRENT_HASHES)


async def _offload[R](fn: Callable[..., R], *args: str) -> R:
    async with _hash_slots:
        return await asyncio.to_thread(fn, *args)


async def hash_password_async(password: str) -> str:
    return await _offload(hash_password, password)


async def verify_password_async(password_hash: str, password: str) -> bool:
    return await _offload(verify_password, password_hash, password)


async def verify_dummy_async(password: str) -> None:
    await _offload(verify_dummy, password)
