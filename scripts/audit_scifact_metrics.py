"""Cross-check a saved SciFact evaluation report with pytrec_eval."""

import argparse
from importlib.metadata import version
import json
from pathlib import Path

import pytrec_eval

from stratajanus.evaluation.metrics import (
    QueryMetrics,
    evaluate_query,
    summarize_metrics,
)
from stratajanus.evaluation.scifact_data import load_qrels, sha256_file


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QRELS_BY_SPLIT = {
    "validation": PROJECT_ROOT / "data/processed/scifact/qrels/train.tsv",
    "test": PROJECT_ROOT / "data/processed/scifact/qrels/test.tsv",
}
MEASURES = {"ndcg_cut.10", "recall.100", "recip_rank"}
METRIC_KEYS = {
    "ndcg_10": "ndcg_cut_10",
    "recall_100": "recall_100",
    "mrr_10": "recip_rank",
}


def rank_scores(doc_ids: list[str]) -> dict[str, float]:
    """Return strictly descending scores that preserve ranked IDs."""
    count = len(doc_ids)
    return {doc_id: float(count - rank) for rank, doc_id in enumerate(doc_ids)}


def audit_report(report_path: Path, qrels_path: Path) -> dict:
    """Compare a saved report's metrics to pytrec_eval without reranking."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    qrels_fingerprint = report.get("input_sha256", {}).get("qrels")
    actual_fingerprint = sha256_file(qrels_path)
    if qrels_fingerprint and qrels_fingerprint != actual_fingerprint:
        raise ValueError(
            "Qrels fingerprint mismatch: report has "
            f"{qrels_fingerprint}, file has {actual_fingerprint}."
        )

    all_qrels = load_qrels(qrels_path)
    saved_queries = report["per_query"]
    query_ids = set(saved_queries)
    missing_qrels = query_ids - set(all_qrels)
    if missing_qrels:
        raise ValueError(f"Report queries missing from qrels: {sorted(missing_qrels)}")

    qrels = {qid: all_qrels[qid] for qid in query_ids}
    strata_per_query: dict[str, QueryMetrics] = {}
    library_run = {}
    mrr_run = {}
    for qid, detail in saved_queries.items():
        doc_ids = detail["ranked_doc_ids"]
        strata_per_query[qid] = evaluate_query(doc_ids, qrels[qid])
        scores = rank_scores(doc_ids)
        library_run[qid] = scores
        mrr_run[qid] = dict(list(scores.items())[:10])

    evaluator = pytrec_eval.RelevanceEvaluator(qrels, MEASURES)
    library_values = evaluator.evaluate(library_run)
    # recip_rank is unbounded; truncate runs to rank 10 for MRR@10.
    mrr_values = evaluator.evaluate(mrr_run)

    if set(library_values) != query_ids or set(mrr_values) != query_ids:
        raise ValueError("pytrec_eval omitted one or more explicitly supplied queries.")

    stored_per_query = {
        qid: detail["metrics"] for qid, detail in saved_queries.items()
    }
    max_diffs = {name: 0.0 for name in METRIC_KEYS}
    mismatches = []
    for qid in sorted(query_ids):
        for metric, library_metric in METRIC_KEYS.items():
            expected = getattr(strata_per_query[qid], metric)
            library_source = mrr_values if metric == "mrr_10" else library_values
            actual = library_source[qid].get(library_metric, 0.0)
            diff = abs(expected - actual)
            max_diffs[metric] = max(max_diffs[metric], diff)
            stored = stored_per_query[qid][metric]
            if diff > 1e-12 or abs(expected - stored) > 1e-12:
                mismatches.append({
                    "query_id": qid,
                    "metric": metric,
                    "stratajanus": expected,
                    "pytrec_eval": actual,
                    "saved_report": stored,
                })

    macro = summarize_metrics(strata_per_query)
    library_macro = {}
    for metric, library_metric in METRIC_KEYS.items():
        source = mrr_values if metric == "mrr_10" else library_values
        library_macro[metric] = sum(
            source[qid].get(library_metric, 0.0) for qid in query_ids
        ) / len(query_ids)
        saved = report["mean_metrics"][metric]
        if abs(macro[metric] - library_macro[metric]) > 1e-12 or abs(macro[metric] - saved) > 1e-12:
            mismatches.append({
                "query_id": "<macro>",
                "metric": metric,
                "stratajanus": macro[metric],
                "pytrec_eval": library_macro[metric],
                "saved_report": saved,
            })

    return {
        "report": str(report_path),
        "qrels": str(qrels_path),
        "pytrec_eval_version": version("pytrec_eval-terrier"),
        "query_count": len(query_ids),
        "max_absolute_difference": max_diffs,
        "macro_stratajanus": macro,
        "macro_pytrec_eval": library_macro,
        "macro_saved_report": report["mean_metrics"],
        "mismatches": mismatches,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Existing saved evaluation JSON report")
    parser.add_argument("--qrels", type=Path, help="Canonical qrels TSV; inferred from report split by default")
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    qrels_path = args.qrels or QRELS_BY_SPLIT.get(report.get("split"))
    if qrels_path is None:
        parser.error("Cannot infer qrels path; pass --qrels.")
    result = audit_report(args.report, qrels_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["mismatches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
