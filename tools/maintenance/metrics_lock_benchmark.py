#!/usr/bin/env python3
"""Micro-benchmark for TokenEconomyCollector lock contention."""

from __future__ import annotations

import argparse
import threading
import time
from dataclasses import dataclass

from providence_runtime.metrics import TokenEconomyCollector


@dataclass(frozen=True)
class BenchResult:
    threads: int
    iterations_per_thread: int
    total_events: int
    elapsed_s: float
    events_per_s: float
    snapshots_per_thread: int


def _consume_event(i: int) -> dict[str, object]:
    return {
        "event": "economy.token.consume",
        "tokens_input": 100 + (i % 10),
        "tokens_output": 40 + (i % 5),
        "tokens_total": 140 + (i % 15),
        "details": {"model": "gpt-5", "cost_usd": 0.0003},
    }


def run_benchmark(
    *, threads: int, iterations_per_thread: int, snapshots_per_thread: int
) -> BenchResult:
    collector = TokenEconomyCollector()
    start_barrier = threading.Barrier(threads + 1)

    def worker(worker_id: int) -> None:
        start_barrier.wait()
        for i in range(iterations_per_thread):
            collector.ingest(_consume_event(worker_id * iterations_per_thread + i))
            if (
                snapshots_per_thread > 0
                and i % max(1, iterations_per_thread // snapshots_per_thread) == 0
            ):
                collector.snapshot()

    workers = [
        threading.Thread(target=worker, name=f"bench-worker-{i}", args=(i,))
        for i in range(threads)
    ]
    for w in workers:
        w.start()

    started = time.perf_counter()
    start_barrier.wait()
    for w in workers:
        w.join()
    elapsed_s = time.perf_counter() - started

    total_events = threads * iterations_per_thread
    eps = total_events / elapsed_s if elapsed_s > 0 else 0.0
    return BenchResult(
        threads=threads,
        iterations_per_thread=iterations_per_thread,
        total_events=total_events,
        elapsed_s=elapsed_s,
        events_per_s=eps,
        snapshots_per_thread=snapshots_per_thread,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark lock contention for TokenEconomyCollector."
    )
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--iterations", type=int, default=20000)
    parser.add_argument("--snapshots", type=int, default=50)
    args = parser.parse_args()

    result = run_benchmark(
        threads=args.threads,
        iterations_per_thread=args.iterations,
        snapshots_per_thread=args.snapshots,
    )
    print("TokenEconomyCollector Lock Benchmark")
    print(f"threads={result.threads}")
    print(f"iterations_per_thread={result.iterations_per_thread}")
    print(f"total_events={result.total_events}")
    print(f"snapshots_per_thread={result.snapshots_per_thread}")
    print(f"elapsed_s={result.elapsed_s:.4f}")
    print(f"events_per_s={result.events_per_s:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
