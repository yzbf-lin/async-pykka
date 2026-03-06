# Quickstart / 快速上手

This guide gets you from zero to a working actor in minutes.

本指南帮助你在几分钟内完成从零到可运行 Actor 的过程。

## 1. Install dependencies / 安装依赖

```bash
uv venv
uv sync --group dev
```

## 2. Define an actor / 定义一个 Actor

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

## 3. Start actor and call through proxy / 启动并通过代理调用

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

## 4. Use `tell` and `ask` / 使用 `tell` 与 `ask`

Use `tell` for fire-and-forget and `ask` for request-response.

`tell` 用于只发不等，`ask` 用于请求-响应。

```python
ref.tell({"type": "tick"})
result = await ref.ask({"type": "query", "key": "status"})
```

## 5. Handle timeouts / 处理超时

```python
future = ref.ask({"type": "slow_op"})
result = await future.get(timeout=1.0)
```

If timeout is reached, `async_pykka.Timeout` is raised.

超时时会抛出 `async_pykka.Timeout`。

## 6. Stop all actors in current loop / 停止当前 loop 的所有 Actor

```python
results = await async_pykka.ActorRegistry.stop_all(current_loop_only=True)
assert all(results)
```

## 7. Event-loop safety rules / 事件循环安全规则

- EN: Create/start actors inside a running event loop.
- 中文：在运行中的事件循环里创建/启动 Actor。

- EN: Call `tell`/`ask`/`stop` in the same loop where actor was created.
- 中文：`tell`/`ask`/`stop` 必须在 Actor 所在同一 loop 调用。

- EN: Cross-loop calls raise `RuntimeError` by design.
- 中文：跨 loop 调用按设计会抛出 `RuntimeError`。

Verified test case / 已验证测试：`tests/test_cross_loop_and_registry.py`

## 8. Suggested next steps / 下一步建议

1. Run `examples/quickstart_counter.py`.
2. Run `examples/timeout_request.py`.
3. Read `docs/scenarios.md` for real-world architecture patterns.
