from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

import async_pykka


class EchoActor(async_pykka.AsyncioActor):
    async def on_receive(self, message: Any) -> Any:
        return message


def run_in_new_loop(coro_factory: Callable[[], Awaitable[Any]]) -> tuple[str, Any]:
    q: queue.Queue[tuple[str, Any]] = queue.Queue()

    def _worker() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro_factory())
        except BaseException as exc:  # noqa: BLE001
            q.put(("err", exc))
        else:
            q.put(("ok", result))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=5)

    if thread.is_alive():
        raise TimeoutError("worker thread did not finish in time")

    return q.get_nowait()


@pytest.mark.asyncio
async def test_cross_loop_calls_raise_runtime_error() -> None:
    ref = EchoActor.start()

    try:
        status_tell, err_tell = run_in_new_loop(lambda: _foreign_tell(ref))
        status_ask, err_ask = run_in_new_loop(lambda: _foreign_ask(ref))
        status_stop, err_stop = run_in_new_loop(lambda: _foreign_stop(ref))

        assert status_tell == "err"
        assert status_ask == "err"
        assert status_stop == "err"

        assert isinstance(err_tell, RuntimeError)
        assert isinstance(err_ask, RuntimeError)
        assert isinstance(err_stop, RuntimeError)

        assert "different event loop" in str(err_tell)
        assert "different event loop" in str(err_ask)
        assert "different event loop" in str(err_stop)
    finally:
        await ref.stop()


async def _foreign_tell(ref: async_pykka.ActorRef[EchoActor]) -> None:
    ref.tell({"from": "other-loop"})


async def _foreign_ask(ref: async_pykka.ActorRef[EchoActor]) -> None:
    await ref.ask({"from": "other-loop"})


async def _foreign_stop(ref: async_pykka.ActorRef[EchoActor]) -> None:
    await ref.stop()


class DummyRef:
    def __init__(self, bound_loop: asyncio.AbstractEventLoop) -> None:
        self._loop = bound_loop

    def __repr__(self) -> str:
        return "<DummyRef other-loop>"


@pytest.mark.asyncio
async def test_registry_get_by_loop_and_stop_all_current_loop_only() -> None:
    local_ref = EchoActor.start()
    foreign_loop = asyncio.new_event_loop()
    dummy_ref = DummyRef(foreign_loop)

    async_pykka.ActorRegistry._actor_refs.append(dummy_ref)  # type: ignore[arg-type]

    try:
        refs_in_current_loop = async_pykka.ActorRegistry.get_by_loop()
        assert local_ref in refs_in_current_loop
        assert dummy_ref not in refs_in_current_loop

        results = await async_pykka.ActorRegistry.stop_all(current_loop_only=True)
        assert results == [True]
        assert local_ref.is_alive() is False

        all_refs = async_pykka.ActorRegistry.get_all()
        assert dummy_ref in all_refs
    finally:
        async_pykka.ActorRegistry._actor_refs = [
            ref for ref in async_pykka.ActorRegistry._actor_refs if ref is not dummy_ref
        ]
        foreign_loop.close()
