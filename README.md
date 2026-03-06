# async-pykka

Pure asyncio actor framework for Python, extracted as an independent project.

## 中文摘要

`async-pykka` 是一个纯异步（`asyncio`）Actor 模型框架，基于 pykka 社区的异步方向尝试进行工程化完善。它强调以下约束：

- 所有 Actor 操作必须在同一个 event loop 内执行。
- 不支持跨线程/跨 event loop 的 `tell`/`ask`/`stop` 调用。
- 使用 ActorRef + ActorProxy + Future 组织异步并发消息处理。

## Why async-pykka

- Pure asyncio actor model, without threading actor implementations.
- Familiar Pykka-style API (`ActorRef`, `ActorProxy`, `Future`) with async semantics.
- Explicit loop-safety checks to fail fast on wrong-loop calls.
- Designed for application-level actor workflows (robot orchestration, event handling, async task isolation).

## Relationship to Pykka

This project is inspired by and derived from async proposals around Pykka, then further completed and adapted into a standalone asyncio-first actor framework.

See:

- <https://github.com/jodal/pykka/pull/218>
- <https://github.com/x0ul/pykka.git>

Also see [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for license and notice requirements.

## Installation

### With uv

```bash
uv venv
uv sync --group dev
```

### With pip (editable for local development)

```bash
python -m pip install -e .
```

## Quick Start

```python
import asyncio
import async_pykka


class GreeterActor(async_pykka.AsyncioActor):
    def __init__(self, name: str):
        super().__init__()
        self.name = name

    async def greet(self) -> str:
        return f"Hello, {self.name}!"


async def main() -> None:
    ref = GreeterActor.start("World")
    proxy = ref.proxy()

    message = await proxy.greet()
    print(message)

    await ref.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

## Common Usage Patterns

### 1. `tell`: fire-and-forget message

```python
ref.tell({"type": "tick"})
```

### 2. `ask`: request/response

```python
future = ref.ask({"type": "sum", "a": 1, "b": 2})
result = await future
```

### 3. `proxy.set`: set actor attributes safely

```python
proxy = ref.proxy()
await proxy.set("counter", 10)
```

Direct assignment is intentionally blocked:

```python
proxy.counter = 11  # raises AttributeError
```

### 4. Stop all actors in current loop

```python
results = await async_pykka.ActorRegistry.stop_all(current_loop_only=True)
```

### 5. Collect multiple futures

```python
results = await async_pykka.get_all([future_a, future_b, future_c])
```

## Event Loop Safety Rules

Every `ActorRef` is bound to the event loop where the actor was created.

- Calling `tell`/`ask`/`stop` from another loop raises `RuntimeError`.
- Calling actor APIs outside a running event loop also raises `RuntimeError`.

This is by design to avoid subtle cross-loop race conditions.

## Migration Notes (from in-repo module to standalone)

If you previously imported this module from a monorepo-local path, migration is typically:

1. Add this standalone project as dependency source.
2. Keep imports unchanged (`import async_pykka`).
3. Re-run your actor tests; ensure all actor operations remain in one loop.

Public API names are intentionally preserved for compatibility.

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run pytest -q
```

## License

MIT. See [`LICENSE`](LICENSE).

Portions are derived from Apache-2.0 licensed upstream work; comply with retention requirements in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
