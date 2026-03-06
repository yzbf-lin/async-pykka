<div align="center">
  <h1>async-pykka</h1>
  <h3>Asyncio-First Python Actor Model Framework</h3>

  <p>
    <img src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/Concurrency-asyncio--first-0ea5e9?style=flat" alt="Concurrency">
    <img src="https://img.shields.io/badge/license-MIT-22c55e" alt="License">
    <a href="https://github.com/yzbf-lin/async-pykka/actions/workflows/ci.yml"><img src="https://github.com/yzbf-lin/async-pykka/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  </p>

[中文](README.zh-CN.md) | **English**

</div>

---

`async-pykka` is a pure asyncio framework that implements the [Actor model](https://en.wikipedia.org/wiki/Actor_model), inspired by Pykka-style APIs and focused on high-throughput I/O workloads.

[Quick Start Example](examples/quickstart_counter.py) | [Scenarios](docs/scenarios.md) | [Performance](docs/performance.md) | [FAQ](docs/faq.md)

> [!IMPORTANT]
> **Same-loop constraint**
> All actor operations must run in the same event loop. Cross-thread or cross-loop calls fail fast with `RuntimeError`.

## ✨ Highlights

- Familiar Actor model API: `start / proxy / ask / tell / stop`
- Asyncio-first scheduling with no actor thread pool dependency
- Built-in async proxy and registry utilities for large actor sets
- Deterministic loop-bound safety model for production debugging

## 📥 Installation

Latest PyPI release: `0.1.4`

### From PyPI (recommended)

```bash
pip install async-pykka
```

### Pin exact version (optional)

```bash
pip install async-pykka==0.1.4
```

### From Git tag (alternative)

```bash
pip install "git+https://github.com/yzbf-lin/async-pykka.git@v0.1.4"
```

### From source archive (no git required)

```bash
pip install "https://github.com/yzbf-lin/async-pykka/archive/refs/tags/v0.1.4.tar.gz"
```

### From release wheel

```bash
pip install "https://github.com/yzbf-lin/async-pykka/releases/download/v0.1.4/async_pykka-0.1.4-py3-none-any.whl"
```

Import package name: `async_pykka`.

## 🚀 Quick Start

```bash
uv venv
uv sync --group dev
uv run python examples/quickstart_counter.py
uv run pytest -q
```

Expected output: `counter=5`

## 🧩 Minimal Example

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

## 📦 Core API

| API | Description |
| --- | --- |
| `AsyncioActor` | Actor base class |
| `ActorRef.tell(msg)` | Fire-and-forget message send |
| `ActorRef.ask(msg)` | Request-response `Future` |
| `ActorRef.proxy()` | Async proxy facade |
| `ActorProxy.set(name, value)` | Safe actor state mutation |
| `ActorRegistry.stop_all()` | Graceful batch shutdown |
| `Future.get(timeout=...)` | Timeout-aware await |

## 🧠 Common Patterns

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

## ⚡ Network I/O A/B Benchmark

Run A/B benchmark against upstream `pykka`:

```bash
uv sync --group dev --group bench
./scripts/fetch_pykka_repo.sh
uv run python examples/benchmark_network_ab.py --actors 50 --requests 5000 --concurrency 200 --rounds 3
```

Benchmark setup (2026-03-06): `actors=50`, `requests=5000`, `concurrency=200`, `payload_bytes=256`, `rounds=3`, localhost TCP echo server.

<table align="center">
  <tr align="center">
    <td align="center" valign="top">
      <img src="docs/assets/network-ab-throughput.svg" alt="Throughput" width="420">
    </td>
    <td align="center" valign="top">
      <img src="docs/assets/network-ab-p95-latency.svg" alt="p95 Latency" width="420">
    </td>
  </tr>
</table>

| Metric (avg over 3 rounds) | async-pykka | pykka | Delta |
| --- | --- | --- | --- |
| Throughput (req/s) | 29999.08 | 14514.66 | +106.68% |
| Mean latency (ms) | 5.3951 | 11.9221 | 54.75% lower |
| p95 latency (ms) | 6.6906 | 13.9568 | 52.06% lower |
| p99 latency (ms) | 11.8346 | 20.5744 | 42.48% lower |

## 📚 Documentation

- [Quickstart](docs/quickstart.md)
- [Scenarios](docs/scenarios.md)
- [Performance Guide](docs/performance.md)
- [FAQ](docs/faq.md)
- [Glossary](docs/glossary.md)

## 🛠 Development

```bash
uv sync --group dev
uv run ruff check .
uv run pytest -q
```

Maintainer release guide: [`docs/releasing.md`](docs/releasing.md)

## 🙏 Attribution

This project is inspired by async proposals around Pykka and further adapted into a standalone asyncio-first framework.

- <https://github.com/jodal/pykka/pull/218>
- <https://github.com/x0ul/pykka.git>

See: [`ACKNOWLEDGEMENTS.md`](ACKNOWLEDGEMENTS.md), [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

## 📄 License

MIT. See [`LICENSE`](LICENSE).
