# async-pykka

Pure asyncio actor framework for Python, extracted as an independent project.

## 中文摘要

`async-pykka` 是一个纯异步（`asyncio`）Actor 框架，适用于高并发网络交互、状态隔离和事件驱动场景。

- 所有 Actor 操作必须在同一 event loop 内执行。
- 默认通过 `ActorRef` / `ActorProxy` / `Future` 完成异步消息编排。
- 兼容 Pykka 风格 API，但明确只支持 asyncio 模型。

## 5-Minute Quick Start

### 1) Install

```bash
uv venv
uv sync --group dev
```

### 2) Run first example

```bash
uv run python examples/quickstart_counter.py
```

### 3) Run tests

```bash
uv run pytest -q
```

## Core Concepts

| Concept | Role | Typical API |
| --- | --- | --- |
| `AsyncioActor` | Actor base class | `on_start`, `on_receive`, `on_stop` |
| `ActorRef` | Safe message endpoint | `tell`, `ask`, `stop`, `proxy` |
| `ActorProxy` | Async RPC-like access | `await proxy.method()`, `await proxy.set(...)` |
| `Future` | Async result carrier | `await future`, `future.get(timeout=...)` |
| `ActorRegistry` | Actor discovery/control | `get_by_class`, `broadcast`, `stop_all` |

## Practical Scenarios

### 1) Request/Response with timeout

Use `ask()` or proxy method calls when you need a reply:

```python
future = ref.ask({"type": "query", "key": "profile"})
result = await future.get(timeout=1.0)
```

See runnable example: [`examples/timeout_request.py`](examples/timeout_request.py)

### 2) High-frequency notify ingestion

Pattern: Net actor receives packets and pushes notify events into a queue; business actor batches them.

See runnable example: [`examples/notify_batch.py`](examples/notify_batch.py)

### 3) Graceful shutdown for many actors

```python
results = await async_pykka.ActorRegistry.stop_all(current_loop_only=True)
assert all(results)
```

See tests: [`tests/test_onboarding_scenarios.py`](tests/test_onboarding_scenarios.py)

## Performance Positioning (What is better here)

Compared with thread-based actor models in I/O-heavy workloads:

- Lower context-switch pressure by staying on asyncio loop.
- Cleaner state isolation per actor mailbox.
- Natural backpressure design using async queues.
- Easier latency tracking via protocol-level metrics in real systems.

For concrete numbers in your environment, run the benchmark harness:

```bash
uv run python examples/benchmark_ping.py --actors 200 --requests 20000 --concurrency 500
```

Benchmark guide: [`docs/performance.md`](docs/performance.md)

## Documentation Map

- Quickstart: [`docs/quickstart.md`](docs/quickstart.md)
- Real-world scenarios: [`docs/scenarios.md`](docs/scenarios.md)
- Performance and benchmark: [`docs/performance.md`](docs/performance.md)

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run pytest -q
```

## Relationship to Pykka

This project is inspired by and derived from async proposals around Pykka, then further completed and adapted into a standalone asyncio-first actor framework.

- <https://github.com/jodal/pykka/pull/218>
- <https://github.com/x0ul/pykka.git>

See [`ACKNOWLEDGEMENTS.md`](ACKNOWLEDGEMENTS.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for attribution and notices.

## License

MIT. See [`LICENSE`](LICENSE).
