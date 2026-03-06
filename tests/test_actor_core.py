from __future__ import annotations

import asyncio

import pytest

import async_pykka


class CounterActor(async_pykka.AsyncioActor):
    def __init__(self) -> None:
        super().__init__()
        self.started = False
        self.stopped = False
        self.counter = 0

    async def on_start(self) -> None:
        self.started = True

    async def on_stop(self) -> None:
        self.stopped = True

    async def on_receive(self, message: dict[str, int | str]) -> int | None:
        msg_type = message.get("type")
        if msg_type == "inc":
            self.counter += int(message.get("value", 1))
            return None
        if msg_type == "get":
            return self.counter
        return None

    async def add(self, a: int, b: int) -> int:
        return a + b

    async def fail(self) -> None:
        raise ValueError("boom")


@pytest.mark.asyncio
async def test_lifecycle_and_stop_idempotency() -> None:
    ref = CounterActor.start()
    proxy = ref.proxy()

    await asyncio.sleep(0)
    assert await proxy.started is True
    assert ref.is_alive() is True

    first = await ref.stop()
    second = await ref.stop()

    assert first is True
    assert second is False
    assert ref.is_alive() is False


@pytest.mark.asyncio
async def test_tell_and_ask_flow() -> None:
    ref = CounterActor.start()

    try:
        tell_result = ref.tell({"type": "inc", "value": 2})
        assert tell_result is None
        ref.tell({"type": "inc", "value": 3})

        value = await ref.ask({"type": "get"})
        assert value == 5

        sum_value = await ref.ask({"type": "get"}).map(lambda x: x + 1)
        assert sum_value == 6
    finally:
        await ref.stop()


@pytest.mark.asyncio
async def test_proxy_call_set_and_direct_assignment_blocked() -> None:
    ref = CounterActor.start()
    proxy = ref.proxy()

    try:
        assert await proxy.add(1, 2) == 3

        await proxy.set("counter", 10)
        assert await proxy.counter == 10

        with pytest.raises(AttributeError):
            proxy.counter = 11
    finally:
        await ref.stop()


@pytest.mark.asyncio
async def test_exception_propagates_via_future() -> None:
    ref = CounterActor.start()
    proxy = ref.proxy()

    try:
        with pytest.raises(ValueError, match="boom"):
            await proxy.fail()
    finally:
        await ref.stop()


@pytest.mark.asyncio
async def test_actor_dead_error_after_stop() -> None:
    ref = CounterActor.start()
    await ref.stop()

    with pytest.raises(async_pykka.ActorDeadError):
        await ref.ask({"type": "get"})

    with pytest.raises(async_pykka.ActorDeadError):
        ref.tell({"type": "inc", "value": 1})
