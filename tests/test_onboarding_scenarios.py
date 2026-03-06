from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from typing import Any

import pytest

import async_pykka


class CounterActor(async_pykka.AsyncioActor):
    def __init__(self) -> None:
        super().__init__()
        self.value = 0

    async def increment(self, delta: int = 1) -> int:
        self.value += delta
        return self.value

    async def get_value(self) -> int:
        return self.value


class SlowEchoActor(async_pykka.AsyncioActor):
    async def slow_echo(self, value: str, delay: float) -> str:
        await asyncio.sleep(delay)
        return value


class NotifyBatchActor(async_pykka.AsyncioActor):
    def __init__(self) -> None:
        super().__init__()
        self._queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._counts: dict[str, int] = defaultdict(int)

    async def on_start(self) -> None:
        self._queue = asyncio.Queue(maxsize=10000)
        self._worker = asyncio.create_task(self._worker_loop())

    async def on_stop(self) -> None:
        if self._queue is not None:
            self._queue.put_nowait(None)
        if self._worker is not None:
            await asyncio.wait_for(self._worker, timeout=1.0)

    async def on_receive(self, message: dict[str, Any]) -> None:
        if message.get("type") != "notify":
            return
        name = str(message.get("name", "unknown"))
        payload = dict(message.get("payload") or {})
        if self._queue is not None:
            self._queue.put_nowait((name, payload))

    async def wait_count(self, name: str, expected: int, timeout: float = 1.0) -> bool:
        deadline = time.perf_counter() + timeout
        while time.perf_counter() < deadline:
            if self._counts[name] >= expected:
                return True
            await asyncio.sleep(0.001)
        return False

    async def get_count(self, name: str) -> int:
        return self._counts[name]

    async def _worker_loop(self) -> None:
        assert self._queue is not None
        while True:
            item = await self._queue.get()
            if item is None:
                return
            name, _payload = item
            self._counts[name] += 1


class EventCollectorActor(async_pykka.AsyncioActor):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[Any] = []

    async def on_receive(self, message: Any) -> None:
        self.events.append(message)

    async def size(self) -> int:
        return len(self.events)


@pytest.mark.asyncio
async def test_quickstart_counter_scenario() -> None:
    ref = CounterActor.start()
    proxy = ref.proxy()

    try:
        assert await proxy.increment(2) == 2
        assert await proxy.increment(3) == 5
        assert await proxy.get_value() == 5
    finally:
        await ref.stop()


@pytest.mark.asyncio
async def test_timeout_request_scenario() -> None:
    ref = SlowEchoActor.start()
    proxy = ref.proxy()

    try:
        future = proxy.slow_echo("hello", 0.2)
        with pytest.raises(async_pykka.Timeout):
            await future.get(timeout=0.01)

        assert await proxy.slow_echo("ok", 0.001) == "ok"
    finally:
        await ref.stop()


@pytest.mark.asyncio
async def test_notify_batch_scenario() -> None:
    ref = NotifyBatchActor.start()
    proxy = ref.proxy()

    try:
        for _ in range(120):
            ref.tell({"type": "notify", "name": "chat", "payload": {"text": "hi"}})

        reached = await proxy.wait_count("chat", expected=120, timeout=1.0)
        assert reached is True
        assert await proxy.get_count("chat") == 120
    finally:
        await ref.stop()


@pytest.mark.asyncio
async def test_registry_broadcast_scenario() -> None:
    refs = [EventCollectorActor.start() for _ in range(3)]
    proxies = [ref.proxy() for ref in refs]

    try:
        async_pykka.ActorRegistry.broadcast({"type": "tick"}, target_class=EventCollectorActor)
        await asyncio.sleep(0)

        sizes = [await proxy.size() for proxy in proxies]
        assert sizes == [1, 1, 1]
    finally:
        await async_pykka.ActorRegistry.stop_all(current_loop_only=True)


@pytest.mark.asyncio
async def test_stop_all_scenario() -> None:
    refs = [CounterActor.start() for _ in range(3)]

    results = await async_pykka.ActorRegistry.stop_all(current_loop_only=True)
    assert results == [True, True, True]

    assert all(not ref.is_alive() for ref in refs)
