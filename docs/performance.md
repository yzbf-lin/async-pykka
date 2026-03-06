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

## Baseline Benchmark / 基线压测

```bash
uv run python examples/benchmark_ping.py --actors 200 --requests 20000 --concurrency 500
```

## A/B Benchmark (Network I/O): async-pykka vs pykka

### Step 1: prepare dependencies / 准备依赖

```bash
uv sync --group dev --group bench
```

### Step 2: fetch pykka repository / 拉取 pykka 仓库

```bash
./scripts/fetch_pykka_repo.sh
```

This clones to `.benchmarks/pykka-repo`.

会克隆到 `.benchmarks/pykka-repo`。

### Step 3: run A/B network benchmark / 执行网络 I/O A/B 对比

```bash
uv run python examples/benchmark_network_ab.py \
  --actors 50 \
  --requests 5000 \
  --concurrency 200 \
  --payload-bytes 256 \
  --rounds 3 \
  --json-output .benchmarks/network_ab_result.json
```

If `.benchmarks/pykka-repo` does not exist, script falls back to installed pypi `pykka`.

如果 `.benchmarks/pykka-repo` 不存在，脚本会回退使用 pip 安装的 `pykka`。

## Sample result (local run) / 样例结果（本地实测）

Environment / 环境：Apple Silicon (macOS), Python 3.12.10, localhost TCP echo server.

Config / 配置：`actors=50, requests=5000, concurrency=200, payload=256B, rounds=3`。

| Framework | Throughput (req/s) | Mean (ms) | P95 (ms) | P99 (ms) |
| --- | ---: | ---: | ---: | ---: |
| async-pykka | 29909.04 | 5.4030 | 6.6686 | 11.9927 |
| pykka | 14608.27 | 11.7405 | 15.9147 | 21.4616 |

Delta / 差异（async-pykka vs pykka）：

- EN: Throughput +104.74%
- 中文：吞吐提升 +104.74%

- EN: P95 latency improvement +58.10%
- 中文：P95 时延降低 +58.10%

Raw report / 原始报告：`.benchmarks/network_ab_result.json`（由脚本生成，不纳入版本库）。

Note / 说明：实际数值与 CPU、Python 小版本、调度噪声、并发配置密切相关，请以你本机多轮中位数为准。

## Recommended benchmark matrix / 建议压测矩阵

1. EN: `actors`: 50 / 200 / 1000
   中文：`actors`：50 / 200 / 1000
2. EN: `concurrency`: 100 / 500 / 2000
   中文：`concurrency`：100 / 500 / 2000
3. EN: payload size: 64B / 256B / 1KB / 4KB
   中文：payload 大小：64B / 256B / 1KB / 4KB
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
