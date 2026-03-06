# Quickstart

This guide gets you from zero to a working actor in minutes.

## 1. Install dependencies

```bash
uv venv
uv sync --group dev
```

## 2. Define an actor

```python
import async_pykka


class CounterActor(async_pykka.AsyncioActor):
    def __init__(self) -> None:
        super().__init__()
        self.counter = 0

    async def inc(self, value: int = 1) -> int:
        self.counter += value
        return self.counter

    async def get(self) -> int:
        return self.counter
```

## 3. Start actor and call through proxy

```python
import asyncio


async def main() -> None:
    ref = CounterActor.start()
    proxy = ref.proxy()

    await proxy.inc(2)
    await proxy.inc(3)

    assert await proxy.get() == 5
    await ref.stop()


asyncio.run(main())
```

## 4. Use `tell` and `ask`

Use `tell` for fire-and-forget, `ask` for request-response.

```python
ref.tell({"type": "tick"})
result = await ref.ask({"type": "query", "key": "status"})
```

## 5. Handle timeouts

```python
future = ref.ask({"type": "slow_op"})
result = await future.get(timeout=1.0)
```

If the timeout is reached, `async_pykka.Timeout` is raised.

## 6. Stop all actors in current loop

```python
results = await async_pykka.ActorRegistry.stop_all(current_loop_only=True)
assert all(results)
```

## 7. Event-loop safety rules (important)

- Create/start actors inside a running event loop.
- Call `tell`/`ask`/`stop` in the same loop where actor was created.
- Cross-loop calls raise `RuntimeError` by design.

See tests for a verified cross-loop failure case:

- `tests/test_cross_loop_and_registry.py`
