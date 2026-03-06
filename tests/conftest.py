from __future__ import annotations

import pytest_asyncio

import async_pykka


@pytest_asyncio.fixture(autouse=True)
async def cleanup_actor_registry() -> None:
    try:
        await async_pykka.ActorRegistry.stop_all(timeout=0.5, current_loop_only=True)
    except RuntimeError:
        pass
    async_pykka.ActorRegistry._actor_refs.clear()

    yield

    try:
        await async_pykka.ActorRegistry.stop_all(timeout=0.5, current_loop_only=True)
    except RuntimeError:
        pass
    async_pykka.ActorRegistry._actor_refs.clear()
