# async-pykka

Pure asyncio actor framework for Python.

Python 异步 Actor 框架（基于 `asyncio`，无线程 Actor 实现）。

## At A Glance / 快速了解

- EN: `async-pykka` keeps the familiar Pykka-style API while enforcing asyncio-first execution.
- 中文：`async-pykka` 保留了 Pykka 风格 API，同时明确采用 asyncio 优先模型。

- EN: All actor operations must run in the same event loop.
- 中文：所有 Actor 操作必须在同一个事件循环内执行。

- EN: Cross-thread or cross-loop calls fail fast with `RuntimeError`.
- 中文：跨线程/跨事件循环调用会快速失败并抛出 `RuntimeError`。

## 5-Minute Start / 5 分钟上手

### 1) Install / 安装

```bash
uv venv
uv sync --group dev
```

### 2) Run first example / 运行第一个示例

```bash
uv run python examples/quickstart_counter.py
```

Expected output / 预期输出：`counter=5`

### 3) Run tests / 运行测试

```bash
uv run pytest -q
```

## Minimal Example / 最小示例

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

## Core API / 核心 API

| API | EN | 中文 |
| --- | --- | --- |
| `AsyncioActor` | Actor base class | Actor 基类 |
| `ActorRef.tell(msg)` | fire-and-forget | 发送消息不等待返回 |
| `ActorRef.ask(msg)` | request-response future | 请求-响应 Future |
| `ActorRef.proxy()` | async proxy facade | 异步代理调用入口 |
| `ActorProxy.set(name, value)` | safe actor state mutation | 安全设置 Actor 内部状态 |
| `ActorRegistry.stop_all()` | graceful batch shutdown | 批量优雅关闭 |
| `Future.get(timeout=...)` | timeout-aware await | 支持超时等待 |

## Common Patterns / 常见模式

### Request/Response with timeout / 超时控制的请求响应

```python
future = ref.ask({"type": "query", "key": "profile"})
result = await future.get(timeout=1.0)
```

### Notify queue + batch handling / Notify 入队 + 批处理

- EN: Put high-frequency notify events into queue, then batch consume.
- 中文：高频 notify 先入队，再批量消费，避免业务处理抖动。

Runnable example / 可运行示例：[`examples/notify_batch.py`](examples/notify_batch.py)

### Graceful shutdown / 优雅停机

```python
results = await async_pykka.ActorRegistry.stop_all(current_loop_only=True)
assert all(results)
```

## Documentation / 文档索引

- [Quickstart / 快速上手](docs/quickstart.md)
- [Scenarios / 场景说明](docs/scenarios.md)
- [Performance / 性能指南](docs/performance.md)
- [FAQ / 常见问题](docs/faq.md)
- [Glossary / 术语表](docs/glossary.md)

## Learning Path / 推荐阅读顺序

1. EN: `docs/quickstart.md` -> run examples.
2. 中文：先看 `docs/quickstart.md`，并运行 `examples/` 下示例。
3. EN: Move to `docs/scenarios.md` for architecture patterns.
4. 中文：再看 `docs/scenarios.md` 理解架构模式。
5. EN: Use `docs/performance.md` for benchmark and tuning.
6. 中文：最后参考 `docs/performance.md` 做基准与调优。

## Performance Positioning / 性能定位

- EN: Optimized for I/O-heavy workloads with asyncio scheduling and mailbox isolation.
- 中文：针对 I/O 密集型负载优化，核心优势是 asyncio 调度与邮箱隔离。

Run benchmark / 运行基准：

```bash
uv run python examples/benchmark_ping.py --actors 200 --requests 20000 --concurrency 500
```

## Development / 开发命令

```bash
uv sync --group dev
uv run ruff check .
uv run pytest -q
```

## Attribution / 致谢来源

This project is inspired by async proposals around Pykka and further adapted into a standalone asyncio-first framework.

本项目基于 Pykka 社区异步方向提案进行扩展和工程化完善。

- <https://github.com/jodal/pykka/pull/218>
- <https://github.com/x0ul/pykka.git>

See / 参见：[`ACKNOWLEDGEMENTS.md`](ACKNOWLEDGEMENTS.md), [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

## License / 许可证

MIT. See [`LICENSE`](LICENSE).
