# async-pykka

基于 `asyncio` 的纯异步 Python Actor 框架。

[英文文档](README.md)

## 项目概览

- `async-pykka` 保留了 Pykka 风格 API，同时采用 asyncio-first 执行模型。
- 所有 Actor 操作必须在同一个事件循环内执行。
- 跨线程或跨事件循环调用会快速失败并抛出 `RuntimeError`。

## 5 分钟上手

### 1) 安装

```bash
uv venv
uv sync --group dev
```

### 2) 运行第一个示例

```bash
uv run python examples/quickstart_counter.py
```

预期输出：`counter=5`

### 3) 运行测试

```bash
uv run pytest -q
```

## 最小示例

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

## 核心 API

| API | 说明 |
| --- | --- |
| `AsyncioActor` | Actor 基类 |
| `ActorRef.tell(msg)` | 发送消息，不等待返回 |
| `ActorRef.ask(msg)` | 请求-响应 `Future` |
| `ActorRef.proxy()` | 异步代理调用入口 |
| `ActorProxy.set(name, value)` | 安全设置 Actor 内部状态 |
| `ActorRegistry.stop_all()` | 批量优雅关闭 |
| `Future.get(timeout=...)` | 支持超时等待 |

## 常见模式

### 带超时的请求响应

```python
future = ref.ask({"type": "query", "key": "profile"})
result = await future.get(timeout=1.0)
```

### Notify 入队 + 批处理

高频 notify 事件先入队，再批量消费，避免处理抖动。

可运行示例：[`examples/notify_batch.py`](examples/notify_batch.py)

### 优雅停机

```python
results = await async_pykka.ActorRegistry.stop_all(current_loop_only=True)
assert all(results)
```

## 文档索引

- [快速上手](docs/quickstart.md)
- [场景说明](docs/scenarios.md)
- [性能指南](docs/performance.md)
- [常见问题](docs/faq.md)
- [术语表](docs/glossary.md)

## 推荐阅读顺序

1. 先看 `docs/quickstart.md` 并运行示例。
2. 再看 `docs/scenarios.md` 理解架构模式。
3. 最后参考 `docs/performance.md` 做基准与调优。

## 性能定位

针对 I/O 密集型负载优化，核心优势是 asyncio 调度与邮箱隔离。

运行基准测试：

```bash
uv run python examples/benchmark_ping.py --actors 200 --requests 20000 --concurrency 500
```

运行与 pykka 的网络 I/O A/B 对比：

```bash
uv sync --group dev --group bench
./scripts/fetch_pykka_repo.sh
uv run python examples/benchmark_network_ab.py --actors 50 --requests 5000 --concurrency 200 --rounds 3
```

### 最新 A/B 测试结果（2026-03-06）

测试配置：`actors=50`、`requests=5000`、`concurrency=200`、`payload_bytes=256`、`rounds=3`，本地 TCP echo 服务（`127.0.0.1`），`pykka` 来源为 pip。

图例：`蓝色 = async-pykka`，`橙色 = pykka`

![网络 I/O 吞吐对比](docs/assets/network-ab-throughput.svg)

![网络 I/O p95 延迟对比](docs/assets/network-ab-p95-latency.svg)

| 指标（3 轮平均） | async-pykka | pykka | 差异 |
| --- | --- | --- | --- |
| 吞吐 (req/s) | 29999.08 | 14514.66 | +106.68% |
| 平均延迟 (ms) | 5.3951 | 11.9221 | 降低 54.75% |
| p95 延迟 (ms) | 6.6906 | 13.9568 | 降低 52.06% |
| p99 延迟 (ms) | 11.8346 | 20.5744 | 降低 42.48% |

详情见：[`docs/performance.md`](docs/performance.md)

## 开发命令

```bash
uv sync --group dev
uv run ruff check .
uv run pytest -q
```

## 致谢来源

本项目基于 Pykka 社区异步方向提案进行扩展和工程化完善。

- <https://github.com/jodal/pykka/pull/218>
- <https://github.com/x0ul/pykka.git>

参见：[`ACKNOWLEDGEMENTS.md`](ACKNOWLEDGEMENTS.md), [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

## 许可证

MIT，详见 [`LICENSE`](LICENSE)。
