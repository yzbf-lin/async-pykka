# Performance Guide / 性能指南

This guide explains what to measure and how to benchmark async-pykka fairly.

本指南说明该测什么、怎么测，帮助你客观评估 async-pykka 性能。

## What async-pykka optimizes / async-pykka 优化点

- EN: Asyncio-native scheduling for I/O-heavy actor workloads.
- 中文：面向 I/O 密集 Actor 负载的 asyncio 原生调度。

- EN: Per-actor mailbox isolation for safer mutable state handling.
- 中文：每个 Actor 的邮箱隔离，降低可变状态并发冲突。

- EN: Queue-based buffering for notify burst smoothing.
- 中文：基于队列的缓冲设计，平滑 notify 突发流量。

- EN: Future-based request multiplexing with timeout control.
- 中文：基于 Future 的请求多路复用和超时控制。

## Benchmark harness / 基准工具

```bash
uv run python examples/benchmark_ping.py --actors 200 --requests 20000 --concurrency 500
```

## Recommended benchmark matrix / 建议压测矩阵

1. EN: `actors`: 50 / 200 / 1000
   中文：`actors`：50 / 200 / 1000
2. EN: `concurrency`: 100 / 500 / 2000
   中文：`concurrency`：100 / 500 / 2000
3. EN: payload size: tiny / medium / large
   中文：payload 大小：小 / 中 / 大
4. EN: timeout policy: none / strict
   中文：超时策略：无 / 严格

## Metrics to capture / 采集指标

- Throughput (req/s) / 吞吐（req/s）
- Mean latency / 平均时延
- P95/P99 latency / P95/P99 时延
- Timeout ratio / 超时率
- Error ratio / 错误率

## Interpreting results / 结果解读

- EN: If throughput plateaus while P99 spikes, event-loop or downstream I/O is likely saturated.
- 中文：若吞吐进入平台期且 P99 飙升，通常是事件循环或下游 I/O 饱和。

- EN: If timeout ratio rises before CPU is high, tune timeout and inspect dependency latency first.
- 中文：若 CPU 未高但超时率上升，优先检查依赖时延与超时阈值配置。

## Fair comparison tips / 公平对比建议

- EN: Keep the same hardware and Python version.
- 中文：保持相同硬件和 Python 版本。

- EN: Warm up before collecting samples.
- 中文：先预热再采样。

- EN: Run at least 3 rounds and report median.
- 中文：至少跑 3 轮并报告中位数。
