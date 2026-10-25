"""Retrieval-quality metrics for ranked external document IDs."""

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class QueryMetrics:
    """Retrieval metrics calculated for one query."""

    ndcg_10: float
    recall_100: float
    mrr_10: float


def _dcg(relevances: Sequence[int]) -> float:
    """Calculate discounted cumulative gain for ranked relevances."""
    return sum(
        (2**relevance - 1) / math.log2(rank + 1)
        for rank, relevance in enumerate(relevances, start=1)
    )


def evaluate_query(
    ranked_doc_ids: Sequence[str],
    judgments: Mapping[str, int],
) -> QueryMetrics:
    """Evaluate one ranked result list against one query's qrels.

    Args:
        ranked_doc_ids: External document IDs in rank order.
        judgments: Mapping of external document ID to nonnegative
            integer relevance. Missing IDs are treated as unjudged
            and receive zero gain for benchmark scoring.

    Returns:
        nDCG@10, Recall@100, and reciprocal rank at 10.

    Raises:
        ValueError: If IDs are duplicated or invalid, judgments are
            invalid, or no document has positive relevance.
    """
    if any(
        not isinstance(doc_id, str) or not doc_id
        for doc_id in ranked_doc_ids
    ):
        raise ValueError(
            "Ranked document IDs must be nonempty strings."
        )

    if len(set(ranked_doc_ids)) != len(ranked_doc_ids):
        raise ValueError("Ranked document IDs must be unique.")

    if any(
        not isinstance(doc_id, str)
        or not doc_id
        or type(relevance) is not int
        or relevance < 0
        for doc_id, relevance in judgments.items()
    ):
        raise ValueError(
            "Judgments need nonempty string IDs and "
            "nonnegative integer relevance values."
        )

    relevant_ids = {
        doc_id
        for doc_id, relevance in judgments.items()
        if relevance > 0
    }

    if not relevant_ids:
        raise ValueError(
            "A query needs at least one judged-relevant document."
        )

    first_ten_relevances = [
        judgments.get(doc_id, 0)
        for doc_id in ranked_doc_ids[:10]
    ]

    ideal_relevances = sorted(
        judgments.values(),
        reverse=True,
    )[:10]

    ndcg_10 = (
        _dcg(first_ten_relevances)
        / _dcg(ideal_relevances)
    )

    retrieved_relevant = relevant_ids.intersection(
        ranked_doc_ids[:100]
    )

    recall_100 = (
        len(retrieved_relevant) / len(relevant_ids)
    )

    reciprocal_rank = 0.0

    for rank, doc_id in enumerate(
        ranked_doc_ids[:10],
        start=1,
    ):
        if doc_id in relevant_ids:
            reciprocal_rank = 1.0 / rank
            break

    return QueryMetrics(
        ndcg_10=ndcg_10,
        recall_100=recall_100,
        mrr_10=reciprocal_rank,
    )


def summarize_metrics(
    per_query: Mapping[str, QueryMetrics],
) -> dict[str, float]:
    """Calculate the arithmetic mean of each metric across queries."""
    if not per_query:
        raise ValueError("Cannot summarize an empty evaluation.")

    return {
        "ndcg_10": statistics.mean(
            item.ndcg_10 for item in per_query.values()
        ),
        "recall_100": statistics.mean(
            item.recall_100 for item in per_query.values()
        ),
        "mrr_10": statistics.mean(
            item.mrr_10 for item in per_query.values()
        ),
    }