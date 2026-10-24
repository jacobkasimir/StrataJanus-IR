"""Utilities for measuring warmed-up, single-client query latency."""

import math
import random
import statistics
import time
from collections.abc import Sequence

from stratajanus.retrieval.bm25 import BM25


def percentile(values: Sequence[float], percent: float) -> float:
    """Calculate a percentile using linear interpolation.

    Args:
        values: Nonempty collection of finite measurements.
        percent: Requested percentile between 0 and 100.

    Returns:
        The interpolated percentile.

    Raises:
        ValueError: If the input or requested percentile is invalid.
    """
    if not values:
        raise ValueError("Percentile requires at least one value.")

    if not math.isfinite(percent) or not 0 <= percent <= 100:
        raise ValueError("Percentile must be between 0 and 100.")

    if any(not math.isfinite(value) for value in values):
        raise ValueError("Measurements must be finite.")

    ordered = sorted(values)

    position = (len(ordered) - 1) * percent / 100
    lower = math.floor(position)
    upper = math.ceil(position)

    weight = position - lower

    return (
        ordered[lower] * (1 - weight)
        + ordered[upper] * weight
    )


def latency_summary(samples_ms: Sequence[float]) -> dict:
    """Summarize latency observations measured in milliseconds."""
    if not samples_ms:
        raise ValueError("At least one latency sample is required.")

    if any(
        not math.isfinite(value) or value < 0
        for value in samples_ms
    ):
        raise ValueError("Latencies must be finite and nonnegative.")

    return {
        "count": len(samples_ms),
        "mean_ms": statistics.mean(samples_ms),
        "p50_ms": percentile(samples_ms, 50),
        "p95_ms": percentile(samples_ms, 95),
        "min_ms": min(samples_ms),
        "max_ms": max(samples_ms),
    }


def benchmark_queries(
    ranker: BM25,
    queries: Sequence[tuple[str, str]],
    *,
    top_k: int = 10,
    repeats: int = 5,
    warmup_rounds: int = 1,
    seed: int = 42,
) -> dict:
    """Measure sequential BM25 searches after an untimed warm-up.

    Args:
        ranker: Initialized BM25 ranker with an index already in memory.
        queries: Pairs of query ID and query text.
        top_k: Maximum number of results per query.
        repeats: Number of measured rounds over the workload.
        warmup_rounds: Number of unmeasured rounds.
        seed: Seed controlling query order within measured rounds.

    Returns:
        Summary statistics and every individual observation.

    Query timings exclude index loading, result display, and the
    bookkeeping performed after each search.
    """
    if not queries:
        raise ValueError("The query workload must not be empty.")

    if repeats <= 0:
        raise ValueError("repeats must be positive.")

    if warmup_rounds < 0:
        raise ValueError("warmup_rounds must not be negative.")

    if top_k <= 0:
        raise ValueError("top_k must be positive.")

    for _ in range(warmup_rounds):
        for _, query_text in queries:
            ranker.search(query_text, top_k=top_k)

    generator = random.Random(seed)
    samples = []

    for repeat in range(repeats):
        order = list(queries)
        generator.shuffle(order)

        for query_id, query_text in order:
            start = time.perf_counter_ns()

            results = ranker.search(query_text, top_k=top_k)

            elapsed_ms = (
                time.perf_counter_ns() - start
            ) / 1_000_000

            samples.append({
                "query_id": query_id,
                "repeat": repeat,
                "latency_ms": elapsed_ms,
                "result_count": len(results),
            })

            # Release results outside the measured interval.
            del results

    return {
        "summary": latency_summary([
            sample["latency_ms"]
            for sample in samples
        ]),
        "samples": samples,
    }