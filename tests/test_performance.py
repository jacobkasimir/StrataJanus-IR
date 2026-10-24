import pytest

from stratajanus.evaluation.performance import (
    benchmark_queries,
    latency_summary,
    percentile,
)
from stratajanus.index.inverted import build_index
from stratajanus.retrieval.bm25 import BM25


def test_percentiles_use_linear_interpolation():
    values = [1, 2, 3, 4, 5]

    assert percentile(values, 0) == 1
    assert percentile(values, 50) == 3
    assert percentile(values, 95) == pytest.approx(4.8)
    assert percentile(values, 100) == 5


def test_single_value_percentile():
    assert percentile([7], 95) == 7


def test_empty_values_are_rejected():
    with pytest.raises(ValueError):
        percentile([], 50)


def test_latency_summary():
    result = latency_summary([1, 2, 3, 4, 5])

    assert result["count"] == 5
    assert result["mean_ms"] == 3
    assert result["p50_ms"] == 3
    assert result["p95_ms"] == pytest.approx(4.8)


@pytest.mark.parametrize("samples", [[-1], [float("nan")]])
def test_invalid_latencies_are_rejected(samples):
    with pytest.raises(ValueError):
        latency_summary(samples)


def test_benchmark_records_each_query_each_round():
    index = build_index([
        {"doc_id": "a", "title": "", "text": "neural search"},
        {"doc_id": "b", "title": "", "text": "search engine"},
    ])

    queries = [
        ("q1", "search"),
        ("q2", "neural"),
    ]

    result = benchmark_queries(
        BM25(index),
        queries,
        repeats=3,
        warmup_rounds=1,
        seed=42,
    )

    assert result["summary"]["count"] == 6

    assert {
        (sample["query_id"], sample["repeat"])
        for sample in result["samples"]
    } == {
        (query_id, repeat)
        for query_id, _ in queries
        for repeat in range(3)
    }

    assert all(
        sample["latency_ms"] >= 0
        for sample in result["samples"]
    )