from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import contextlib
import importlib
import json
import os
import socket
import struct
import sys
import threading
import time
from pathlib import Path

import async_pykka


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if p <= 0:
        return values[0]
    if p >= 100:
        return values[-1]
    index = int((p / 100.0) * (len(values) - 1))
    return values[index]


def safe_pct(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return (numerator / denominator) * 100.0


class EchoServerThread(threading.Thread):
    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self._ready = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._server: asyncio.Server | None = None
        self._error: BaseException | None = None

    def start_and_wait(self, timeout: float = 5.0) -> None:
        self.start()
        if not self._ready.wait(timeout=timeout):
            raise TimeoutError("echo server failed to start in time")
        if self._error is not None:
            raise RuntimeError(f"echo server startup failed: {self._error}") from self._error

    def run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._server = self._loop.run_until_complete(asyncio.start_server(self._handle_client, self.host, self.port))
            sock = self._server.sockets[0]
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            address = sock.getsockname()
            self.host = str(address[0])
            self.port = int(address[1])
            self._ready.set()
            self._loop.run_forever()
        except BaseException as exc:  # noqa: BLE001
            self._error = exc
            self._ready.set()
        finally:
            if self._loop is not None:
                self._loop.run_until_complete(self._shutdown())
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                self._loop.close()

    async def _shutdown(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                header = await reader.readexactly(4)
                payload_len = struct.unpack("!I", header)[0]
                payload = await reader.readexactly(payload_len)
                writer.write(header + payload)
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            writer.close()
            with contextlib.suppress(Exception):
                await writer.wait_closed()

    def stop(self) -> None:
        if self._loop is None:
            return
        if self._loop.is_closed():
            return

        future = asyncio.run_coroutine_threadsafe(self._shutdown(), self._loop)
        with contextlib.suppress(Exception):
            future.result(timeout=3)

        self._loop.call_soon_threadsafe(self._loop.stop)
        self.join(timeout=3)


class AsyncioNetEchoActor(async_pykka.AsyncioActor):
    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self._host = host
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def on_start(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self._host, self._port)
        sock = self._writer.get_extra_info("socket")
        if sock is not None:
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    async def on_stop(self) -> None:
        if self._writer is None:
            return
        self._writer.close()
        with contextlib.suppress(Exception):
            await self._writer.wait_closed()

    async def request(self, payload: bytes) -> bytes:
        if self._reader is None or self._writer is None:
            raise RuntimeError("connection not initialized")

        header = struct.pack("!I", len(payload))
        self._writer.write(header + payload)
        await self._writer.drain()

        result_header = await self._reader.readexactly(4)
        result_len = struct.unpack("!I", result_header)[0]
        return await self._reader.readexactly(result_len)


def build_result(framework: str, requests: int, elapsed_sec: float, latencies_ms: list[float]) -> dict[str, float | str | int]:
    latencies_sorted = sorted(latencies_ms)
    throughput = requests / elapsed_sec if elapsed_sec > 0 else 0.0
    mean_latency = sum(latencies_sorted) / len(latencies_sorted) if latencies_sorted else 0.0

    return {
        "framework": framework,
        "requests": requests,
        "elapsed_sec": elapsed_sec,
        "throughput_rps": throughput,
        "latency_mean_ms": mean_latency,
        "latency_p50_ms": percentile(latencies_sorted, 50),
        "latency_p95_ms": percentile(latencies_sorted, 95),
        "latency_p99_ms": percentile(latencies_sorted, 99),
    }


async def run_async_pykka_round(host: str, port: int, actors: int, requests: int, concurrency: int, payload: bytes) -> dict[str, float | str | int]:
    refs = [AsyncioNetEchoActor.start(host, port) for _ in range(actors)]
    proxies = [ref.proxy() for ref in refs]

    latencies_ms: list[float] = []
    semaphore = asyncio.Semaphore(concurrency)

    async def do_one(index: int) -> None:
        proxy = proxies[index % len(proxies)]
        async with semaphore:
            start = time.perf_counter()
            response = await proxy.request(payload)
            if response != payload:
                raise RuntimeError("async_pykka payload mismatch")
            latencies_ms.append((time.perf_counter() - start) * 1000)

    start_total = time.perf_counter()
    try:
        await asyncio.gather(*(do_one(i) for i in range(requests)))
    finally:
        await async_pykka.ActorRegistry.stop_all(current_loop_only=True)

    elapsed_sec = time.perf_counter() - start_total
    return build_result("async_pykka", requests, elapsed_sec, latencies_ms)


def import_pykka(pykka_repo: str | None) -> object:
    if pykka_repo:
        repo_path = Path(pykka_repo).expanduser().resolve()
        src_path = repo_path / "src"
        if src_path.exists() and (src_path / "pykka").exists():
            sys.path.insert(0, str(src_path))
        elif (repo_path / "pykka").exists():
            sys.path.insert(0, str(repo_path))
    return importlib.import_module("pykka")


def recv_exact(sock: socket.socket, n: int) -> bytes:
    chunks: list[bytes] = []
    remaining = n
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("socket closed while reading")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def run_pykka_round(
    host: str,
    port: int,
    actors: int,
    requests: int,
    concurrency: int,
    payload: bytes,
    timeout_seconds: float,
    pykka_repo: str | None,
) -> dict[str, float | str | int]:
    pykka = import_pykka(pykka_repo)

    class PykkaNetEchoActor(pykka.ThreadingActor):
        def __init__(self, target_host: str, target_port: int) -> None:
            super().__init__()
            self._host = target_host
            self._port = target_port
            self._sock: socket.socket | None = None

        def on_start(self) -> None:
            self._sock = socket.create_connection((self._host, self._port), timeout=5)
            self._sock.settimeout(timeout_seconds)
            self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        def on_stop(self) -> None:
            if self._sock is not None:
                with contextlib.suppress(Exception):
                    self._sock.close()
                self._sock = None

        def request(self, data: bytes) -> bytes:
            if self._sock is None:
                raise RuntimeError("socket not initialized")
            header = struct.pack("!I", len(data))
            self._sock.sendall(header + data)
            result_header = recv_exact(self._sock, 4)
            result_len = struct.unpack("!I", result_header)[0]
            return recv_exact(self._sock, result_len)

    refs = [PykkaNetEchoActor.start(host, port) for _ in range(actors)]
    proxies = [ref.proxy() for ref in refs]

    def do_one(index: int) -> float:
        start = time.perf_counter()
        future = proxies[index % len(proxies)].request(payload)
        response = future.get(timeout=timeout_seconds)
        if response != payload:
            raise RuntimeError("pykka payload mismatch")
        return (time.perf_counter() - start) * 1000

    latencies_ms: list[float] = []
    start_total = time.perf_counter()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(do_one, i) for i in range(requests)]
            for future in concurrent.futures.as_completed(futures):
                latencies_ms.append(future.result())
    finally:
        for ref in refs:
            with contextlib.suppress(Exception):
                ref.stop(block=True, timeout=2)

    elapsed_sec = time.perf_counter() - start_total
    return build_result("pykka", requests, elapsed_sec, latencies_ms)


def aggregate_results(results: list[dict[str, float | str | int]]) -> dict[str, float]:
    keys = [
        "elapsed_sec",
        "throughput_rps",
        "latency_mean_ms",
        "latency_p50_ms",
        "latency_p95_ms",
        "latency_p99_ms",
    ]
    agg: dict[str, float] = {}
    for key in keys:
        values = [float(item[key]) for item in results]
        agg[key] = sum(values) / len(values)
    return agg


def print_single_result(title: str, result: dict[str, float | str | int]) -> None:
    print(f"{title}")
    print(
        "  "
        f"throughput={float(result['throughput_rps']):.2f} req/s, "
        f"mean={float(result['latency_mean_ms']):.4f} ms, "
        f"p95={float(result['latency_p95_ms']):.4f} ms, "
        f"p99={float(result['latency_p99_ms']):.4f} ms"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="A/B benchmark: async-pykka vs pykka on TCP network I/O")
    parser.add_argument("--actors", type=int, default=50)
    parser.add_argument("--requests", type=int, default=5000)
    parser.add_argument("--concurrency", type=int, default=200)
    parser.add_argument("--payload-bytes", type=int, default=256)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--pykka-repo", type=str, default=".benchmarks/pykka-repo")
    parser.add_argument("--json-output", type=str, default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.actors <= 0 or args.requests <= 0 or args.concurrency <= 0 or args.rounds <= 0:
        raise ValueError("actors/requests/concurrency/rounds must be positive")

    pykka_repo = args.pykka_repo
    if pykka_repo and not Path(pykka_repo).exists():
        pykka_repo = None

    payload = os.urandom(args.payload_bytes)
    server = EchoServerThread()
    server.start_and_wait()

    print("=== network I/O A/B benchmark ===")
    print(f"server={server.host}:{server.port}")
    print(
        f"actors={args.actors}, requests={args.requests}, concurrency={args.concurrency}, "
        f"payload_bytes={args.payload_bytes}, rounds={args.rounds}"
    )
    print(f"pykka_source={'repo' if pykka_repo else 'pip'}")

    async_rounds: list[dict[str, float | str | int]] = []
    pykka_rounds: list[dict[str, float | str | int]] = []

    try:
        for round_idx in range(1, args.rounds + 1):
            print(f"\n-- round {round_idx} --")
            async_result = asyncio.run(
                run_async_pykka_round(
                    server.host,
                    server.port,
                    args.actors,
                    args.requests,
                    args.concurrency,
                    payload,
                )
            )
            pykka_result = run_pykka_round(
                server.host,
                server.port,
                args.actors,
                args.requests,
                args.concurrency,
                payload,
                args.timeout_seconds,
                pykka_repo,
            )

            async_rounds.append(async_result)
            pykka_rounds.append(pykka_result)

            print_single_result("async-pykka", async_result)
            print_single_result("pykka", pykka_result)

            throughput_adv = safe_pct(
                float(async_result["throughput_rps"]) - float(pykka_result["throughput_rps"]),
                float(pykka_result["throughput_rps"]),
            )
            p95_improve = safe_pct(
                float(pykka_result["latency_p95_ms"]) - float(async_result["latency_p95_ms"]),
                float(pykka_result["latency_p95_ms"]),
            )
            print(f"  delta: throughput={throughput_adv:+.2f}% (async-pykka vs pykka), p95_latency={p95_improve:+.2f}%")

    finally:
        server.stop()

    async_agg = aggregate_results(async_rounds)
    pykka_agg = aggregate_results(pykka_rounds)

    throughput_adv_avg = safe_pct(
        async_agg["throughput_rps"] - pykka_agg["throughput_rps"],
        pykka_agg["throughput_rps"],
    )
    p95_improve_avg = safe_pct(
        pykka_agg["latency_p95_ms"] - async_agg["latency_p95_ms"],
        pykka_agg["latency_p95_ms"],
    )

    print("\n=== average over rounds ===")
    print(
        "async-pykka: "
        f"throughput={async_agg['throughput_rps']:.2f} req/s, "
        f"mean={async_agg['latency_mean_ms']:.4f} ms, "
        f"p95={async_agg['latency_p95_ms']:.4f} ms, "
        f"p99={async_agg['latency_p99_ms']:.4f} ms"
    )
    print(
        "pykka:      "
        f"throughput={pykka_agg['throughput_rps']:.2f} req/s, "
        f"mean={pykka_agg['latency_mean_ms']:.4f} ms, "
        f"p95={pykka_agg['latency_p95_ms']:.4f} ms, "
        f"p99={pykka_agg['latency_p99_ms']:.4f} ms"
    )
    print(
        "delta: "
        f"throughput={throughput_adv_avg:+.2f}% (higher is better), "
        f"p95_latency={p95_improve_avg:+.2f}% (positive means async-pykka lower latency)"
    )

    if args.json_output:
        output = {
            "config": {
                "actors": args.actors,
                "requests": args.requests,
                "concurrency": args.concurrency,
                "payload_bytes": args.payload_bytes,
                "rounds": args.rounds,
                "pykka_source": "repo" if pykka_repo else "pip",
            },
            "rounds": {
                "async_pykka": async_rounds,
                "pykka": pykka_rounds,
            },
            "average": {
                "async_pykka": async_agg,
                "pykka": pykka_agg,
                "delta": {
                    "throughput_percent": throughput_adv_avg,
                    "p95_latency_percent": p95_improve_avg,
                },
            },
        }
        Path(args.json_output).write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"json_report={args.json_output}")


if __name__ == "__main__":
    main()
