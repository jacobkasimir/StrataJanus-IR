"""Independent retrieval-metric checks against pytrec_eval-terrier."""

import math

import pytrec_eval
import pytest

from stratajanus.evaluation.metrics import evaluate_query, summarize_metrics
from scripts.audit_scifact_metrics import MEASURES, rank_scores


def compare_one(ranked, judgments):
    """Compare one ranked list, including the bounded MRR convention."""
    qrels = {"q": judgments}
    scores = rank_scores(ranked)
    assert len(set(scores.values())) == len(scores)
    full = pytrec_eval.RelevanceEvaluator(qrels, MEASURES).evaluate(
        {"q": scores}
    )["q"]
    first_ten = dict(list(scores.items())[:10])
    bounded = pytrec_eval.RelevanceEvaluator(
        qrels, {"recip_rank"}
    ).evaluate({"q": first_ten})["q"]["recip_rank"]
    ours = evaluate_query(ranked, judgments)
    assert ours.recall_100 == pytest.approx(full["recall_100"], abs=1e-12)
    assert ours.mrr_10 == pytest.approx(bounded, abs=1e-12)
    return ours, full, bounded


def padded(rank, relevant_id="rel"):
    """Build a ranking with one judged relevant document at the given rank."""
    docs = [f"u{i}" for i in range(rank - 1)]
    docs.append(relevant_id)
    return docs


def test_perfect_ranking_and_reversed_graded_gain():
    perfect, _, _ = compare_one(
        ["grade-2", "grade-1"], {"grade-2": 2, "grade-1": 1}
    )
    assert perfect.ndcg_10 == pytest.approx(1.0)

    reversed_metrics, library, _ = compare_one(
        ["grade-1", "grade-2"], {"grade-2": 2, "grade-1": 1}
    )
    exponential_gain = (1 + 3 / math.log2(3)) / (3 + 1 / math.log2(3))
    linear_gain = (1 + 2 / math.log2(3)) / (2 + 1 / math.log2(3))
    assert reversed_metrics.ndcg_10 == pytest.approx(exponential_gain)
    assert library["ndcg_cut_10"] == pytest.approx(linear_gain)
    assert abs(reversed_metrics.ndcg_10 - library["ndcg_cut_10"]) > 0.01


def test_unjudged_above_relevant():
    metrics, _, _ = compare_one(
        ["unjudged", "relevant"], {"relevant": 1}
    )
    assert metrics.ndcg_10 == pytest.approx(1 / math.log2(3))
    assert metrics.mrr_10 == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("rank", "expected_recall", "expected_mrr"),
    [(10, 1.0, 0.1), (11, 1.0, 0.0), (100, 1.0, 0.0), (101, 0.0, 0.0)],
)
def test_cutoff_boundaries(rank, expected_recall, expected_mrr):
    metrics, _, _ = compare_one(padded(rank), {"rel": 1})
    assert metrics.recall_100 == expected_recall
    assert metrics.mrr_10 == expected_mrr


def test_multiple_relevant_documents_and_empty_results():
    metrics, library, _ = compare_one(
        ["r2", "unjudged", "r1"], {"r1": 1, "r2": 2, "not-retrieved": 1}
    )
    assert metrics.recall_100 == pytest.approx(2 / 3)
    assert library["recall_100"] == pytest.approx(metrics.recall_100)
    empty, _, _ = compare_one([], {"relevant": 2})
    assert empty.ndcg_10 == empty.recall_100 == empty.mrr_10 == 0.0


def test_macro_average_keeps_explicit_empty_query():
    qrels = {"perfect": {"r": 1}, "empty": {"s": 1}}
    runs = {"perfect": rank_scores(["r"]), "empty": {}}
    evaluated = pytrec_eval.RelevanceEvaluator(qrels, MEASURES).evaluate(runs)
    assert set(evaluated) == set(qrels)

    per_query = {
        "perfect": evaluate_query(["r"], qrels["perfect"]),
        "empty": evaluate_query([], qrels["empty"]),
    }
    macro = summarize_metrics(per_query)
    assert macro == pytest.approx({
        "ndcg_10": 0.5,
        "recall_100": 0.5,
        "mrr_10": 0.5,
    })
    assert sum(evaluated[q]["ndcg_cut_10"] for q in qrels) / 2 == pytest.approx(macro["ndcg_10"])
    assert sum(evaluated[q]["recall_100"] for q in qrels) / 2 == pytest.approx(macro["recall_100"])
    assert sum(evaluated[q]["recip_rank"] for q in qrels) / 2 == pytest.approx(macro["mrr_10"])


def test_installed_library_measure_names():
    assert {"ndcg_cut", "recall", "recip_rank"} <= pytrec_eval.supported_measures
    assert "MRR@10" not in pytrec_eval.supported_measures


def test_no_positive_judgments_are_rejected_by_stratajanus():
    with pytest.raises(ValueError, match="at least one"):
        evaluate_query(["document"], {"document": 0})

    # The library scores all-zero qrels as zero rather than rejecting them.
    result = pytrec_eval.RelevanceEvaluator(
        {"q": {"document": 0}}, MEASURES
    ).evaluate({"q": {"document": 1.0}})
    assert result["q"] == {
        "ndcg_cut_10": 0.0,
        "recall_100": 0.0,
        "recip_rank": 0.0,
    }
