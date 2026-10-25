import math

import pytest

from stratajanus.evaluation.metrics import (
    QueryMetrics,
    evaluate_query,
    summarize_metrics,
)


def test_perfect_ranking():
    result = evaluate_query(
        ["most-relevant", "relevant"],
        {
            "most-relevant": 2,
            "relevant": 1,
        },
    )

    assert result.ndcg_10 == pytest.approx(1.0)
    assert result.recall_100 == 1.0
    assert result.mrr_10 == 1.0


def test_reversed_graded_ranking():
    result = evaluate_query(
        ["relevant", "most-relevant"],
        {
            "most-relevant": 2,
            "relevant": 1,
        },
    )

    actual_dcg = 1 + 3 / math.log2(3)
    ideal_dcg = 3 + 1 / math.log2(3)

    assert result.ndcg_10 == pytest.approx(
        actual_dcg / ideal_dcg
    )
    assert result.recall_100 == 1.0
    assert result.mrr_10 == 1.0


def test_first_relevant_document_at_rank_two():
    result = evaluate_query(
        ["unjudged", "relevant"],
        {"relevant": 1},
    )

    assert result.ndcg_10 == pytest.approx(
        1 / math.log2(3)
    )
    assert result.recall_100 == 1.0
    assert result.mrr_10 == 0.5


def test_unretrieved_relevant_document():
    result = evaluate_query(
        ["unjudged"],
        {"relevant": 1},
    )

    assert result == QueryMetrics(
        ndcg_10=0.0,
        recall_100=0.0,
        mrr_10=0.0,
    )


def test_recall_100_cutoff():
    judgments = {"relevant": 1}

    # A relevant document at rank 100 counts toward Recall@100.
    at_rank_100 = [
        f"unjudged-{i}"
        for i in range(99)
    ] + ["relevant"]

    # A relevant document at rank 101 does not.
    at_rank_101 = [
        f"unjudged-{i}"
        for i in range(100)
    ] + ["relevant"]

    assert evaluate_query(
        at_rank_100,
        judgments,
    ).recall_100 == 1.0

    assert evaluate_query(
        at_rank_101,
        judgments,
    ).recall_100 == 0.0


def test_mrr_10_cutoff():
    ranked = [
        f"unjudged-{i}"
        for i in range(10)
    ] + ["relevant"]

    result = evaluate_query(
        ranked,
        {"relevant": 1},
    )

    assert result.mrr_10 == 0.0


def test_duplicate_results_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        evaluate_query(
            ["relevant", "relevant"],
            {"relevant": 1},
        )


def test_query_without_positive_judgment_is_rejected():
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        evaluate_query(
            ["document"],
            {"document": 0},
        )


def test_metric_summary():
    summary = summarize_metrics({
        "q1": QueryMetrics(1.0, 0.5, 1.0),
        "q2": QueryMetrics(0.0, 1.0, 0.0),
    })

    assert summary == {
        "ndcg_10": 0.5,
        "recall_100": 0.75,
        "mrr_10": 0.5,
    }