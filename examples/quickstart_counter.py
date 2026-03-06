from __future__ import annotations

import asyncio

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


async def main() -> None:
    ref = CounterActor.start()
    proxy = ref.proxy()

    await proxy.increment(2)
    await proxy.increment(3)

    current = await proxy.get_value()
    print(f"counter={current}")

    await ref.stop()


if __name__ == "__main__":
    asyncio.run(main())
