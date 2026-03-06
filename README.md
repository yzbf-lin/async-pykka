# async-pykka

Pure asyncio actor framework for Python.

[Chinese README](README.zh-CN.md)

## At A Glance

- `async-pykka` keeps the familiar Pykka-style API while enforcing asyncio-first execution.
- All actor operations must run in the same event loop.
- Cross-thread or cross-loop calls fail fast with `RuntimeError`.

## 5-Minute Start

### 1) Install

```bash
uv venv
uv sync --group dev
```

### 2) Run first example

```bash
uv run python examples/quickstart_counter.py
```

Expected output: `counter=5`

### 3) Run tests

```bash
uv run pytest -q
```

## Minimal Example

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

## Core API

| API | Description |
| --- | --- |
| `AsyncioActor` | Actor base class |
| `ActorRef.tell(msg)` | Fire-and-forget message send |
| `ActorRef.ask(msg)` | Request-response `Future` |
| `ActorRef.proxy()` | Async proxy facade |
| `ActorProxy.set(name, value)` | Safe actor state mutation |
| `ActorRegistry.stop_all()` | Graceful batch shutdown |
| `Future.get(timeout=...)` | Timeout-aware await |

## Common Patterns

### Request/Response with timeout

```python
future = ref.ask({"type": "query", "key": "profile"})
result = await future.get(timeout=1.0)
```

### Notify queue + batch handling

Put high-frequency notify events into a queue, then consume in batches.

Runnable example: [`examples/notify_batch.py`](examples/notify_batch.py)

### Graceful shutdown

```python
results = await async_pykka.ActorRegistry.stop_all(current_loop_only=True)
assert all(results)
```

## Documentation

- [Quickstart](docs/quickstart.md)
- [Scenarios](docs/scenarios.md)
- [Performance](docs/performance.md)
- [FAQ](docs/faq.md)
- [Glossary](docs/glossary.md)

## Learning Path

1. Start from `docs/quickstart.md` and run examples.
2. Move to `docs/scenarios.md` for architecture patterns.
3. Use `docs/performance.md` for benchmark and tuning.

## Performance Positioning

Optimized for I/O-heavy workloads with asyncio scheduling and mailbox isolation.

Run benchmark:

```bash
uv run python examples/benchmark_ping.py --actors 200 --requests 20000 --concurrency 500
```

Run A/B network benchmark vs pykka:

```bash
uv sync --group dev --group bench
./scripts/fetch_pykka_repo.sh
uv run python examples/benchmark_network_ab.py --actors 50 --requests 5000 --concurrency 200 --rounds 3
```

### Latest A/B Result (2026-03-06)

Test config: `actors=50`, `requests=5000`, `concurrency=200`, `payload_bytes=256`, `rounds=3`, local TCP echo server (`127.0.0.1`), `pykka` source from pip.

Legend: `blue = async-pykka`, `orange = pykka`

![Network I/O Throughput Comparison](docs/assets/network-ab-throughput.svg)

![Network I/O p95 Latency Comparison](docs/assets/network-ab-p95-latency.svg)

| Metric (avg over 3 rounds) | async-pykka | pykka | Delta |
| --- | --- | --- | --- |
| Throughput (req/s) | 29999.08 | 14514.66 | +106.68% |
| Mean latency (ms) | 5.3951 | 11.9221 | 54.75% lower |
| p95 latency (ms) | 6.6906 | 13.9568 | 52.06% lower |
| p99 latency (ms) | 11.8346 | 20.5744 | 42.48% lower |

Details: [`docs/performance.md`](docs/performance.md)

## Development

```bash
uv sync --group dev
uv run ruff check .
uv run pytest -q
```

## Attribution

This project is inspired by async proposals around Pykka and further adapted into a standalone asyncio-first framework.

- <https://github.com/jodal/pykka/pull/218>
- <https://github.com/x0ul/pykka.git>

See: [`ACKNOWLEDGEMENTS.md`](ACKNOWLEDGEMENTS.md), [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

## License

MIT. See [`LICENSE`](LICENSE).
