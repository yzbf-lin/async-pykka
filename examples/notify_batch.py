from __future__ import annotations

import asyncio
from collections import defaultdict

import async_pykka


class NotifyBatchActor(async_pykka.AsyncioActor):
    def __init__(self) -> None:
        super().__init__()
        self._queue: asyncio.Queue[dict[str, str] | None] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._counts: dict[str, int] = defaultdict(int)

    async def on_start(self) -> None:
        self._queue = asyncio.Queue(maxsize=10000)
        self._worker = asyncio.create_task(self._worker_loop())

    async def on_stop(self) -> None:
        if self._queue is not None:
            self._queue.put_nowait(None)
        if self._worker is not None:
            await self._worker

    async def on_receive(self, message: dict[str, str]) -> None:
        if message.get("type") != "notify":
            return
        if self._queue is not None:
            self._queue.put_nowait(message)

    async def get_count(self, name: str) -> int:
        return self._counts[name]

    async def _worker_loop(self) -> None:
        assert self._queue is not None
        while True:
            msg = await self._queue.get()
            if msg is None:
                return
            name = msg.get("name", "unknown")
            self._counts[name] += 1


async def main() -> None:
    ref = NotifyBatchActor.start()
    proxy = ref.proxy()

    try:
        for _ in range(100):
            ref.tell({"type": "notify", "name": "chat"})

        await asyncio.sleep(0.02)
        count = await proxy.get_count("chat")
        print(f"chat_count={count}")
    finally:
        await ref.stop()


if __name__ == "__main__":
    asyncio.run(main())
