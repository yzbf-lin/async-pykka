# Performance Guide

This guide explains what to measure and provides a benchmark harness.

## What async-pykka optimizes

- Asyncio-native scheduling for I/O-heavy actor workloads.
- Per-actor mailbox isolation for simpler state consistency.
- Queue-based buffering for push-notify bursts.
- Future-based request multiplexing with explicit timeout handling.

## Benchmark harness

Use the included script:

```bash
uv run python examples/benchmark_ping.py --actors 200 --requests 20000 --concurrency 500
```

## Recommended benchmark matrix

Run multiple combinations and compare:

1. `actors`: 50 / 200 / 1000
2. `concurrency`: 100 / 500 / 2000
3. payload sizes: tiny / medium / large
4. timeout policy: no-timeout / strict-timeout

## Metrics to capture

- Total throughput (req/s)
- Mean latency
- P95/P99 latency
- Timeout ratio
- Error ratio

## Example output interpretation

If throughput rises with concurrency then plateaus while P99 spikes, your bottleneck is likely event-loop saturation or downstream I/O.

If timeout ratio grows before CPU is saturated, review remote dependency latency and timeout values first.

## Fair comparison tips

- Keep same hardware and Python version.
- Warm up before sampling.
- Run at least 3 rounds and report median.
