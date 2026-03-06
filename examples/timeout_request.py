from __future__ import annotations

import asyncio

import async_pykka


class SlowEchoActor(async_pykka.AsyncioActor):
    async def slow_echo(self, value: str, delay: float) -> str:
        await asyncio.sleep(delay)
        return value


async def main() -> None:
    ref = SlowEchoActor.start()
    proxy = ref.proxy()

    try:
        future = proxy.slow_echo("hello", 0.2)
        try:
            result = await future.get(timeout=0.05)
            print(f"result={result}")
        except async_pykka.Timeout:
            print("timeout triggered as expected")
    finally:
        await ref.stop()


if __name__ == "__main__":
    asyncio.run(main())
