from __future__ import annotations

import argparse
import asyncio
import statistics
import time

import async_pykka


class PingActor(async_pykka.AsyncioActor):
    async def ping(self, value: int) -> int:
        return value + 1


async def _worker(proxy: async_pykka.ActorProxy[PingActor], iterations: int, latencies: list[float]) -> None:
    for i in range(iterations):
        start = time.perf_counter()
        result = await proxy.ping(i)
        if result != i + 1:
            raise RuntimeError(f"unexpected result: {result}")
        latencies.append((time.perf_counter() - start) * 1000)


async def run_benchmark(actors: int, requests: int, concurrency: int) -> None:
    refs = [PingActor.start() for _ in range(actors)]
    proxies = [ref.proxy() for ref in refs]

    latencies: list[float] = []
    start_total = time.perf_counter()

    try:
        sem = asyncio.Semaphore(concurrency)

        async def run_task(idx: int) -> None:
            proxy = proxies[idx % actors]
            async with sem:
                await _worker(proxy, 1, latencies)

        await asyncio.gather(*(run_task(i) for i in range(requests)))
    finally:
        await async_pykka.ActorRegistry.stop_all(current_loop_only=True)

    elapsed = time.perf_counter() - start_total
    throughput = requests / elapsed if elapsed > 0 else 0.0

    lat_sorted = sorted(latencies)
    p95 = lat_sorted[int(len(lat_sorted) * 0.95)] if lat_sorted else 0.0
    p99 = lat_sorted[int(len(lat_sorted) * 0.99)] if lat_sorted else 0.0

    print("=== async-pykka ping benchmark ===")
    print(f"actors={actors}, requests={requests}, concurrency={concurrency}")
    print(f"elapsed={elapsed:.4f}s")
    print(f"throughput={throughput:.2f} req/s")
    print(f"latency_mean={statistics.mean(latencies):.4f} ms")
    print(f"latency_p95={p95:.4f} ms")
    print(f"latency_p99={p99:.4f} ms")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark async-pykka ping throughput/latency")
    parser.add_argument("--actors", type=int, default=100)
    parser.add_argument("--requests", type=int, default=10000)
    parser.add_argument("--concurrency", type=int, default=300)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run_benchmark(args.actors, args.requests, args.concurrency))
