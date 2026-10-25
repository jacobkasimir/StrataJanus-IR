"""Evaluate saved SciFact BM25 indexes against relevance judgments."""

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from stratajanus.evaluation.metrics import (
    evaluate_query,
    summarize_metrics,
)
from stratajanus.evaluation.scifact_data import (
    load_qrels,
    load_queries,
    sha256_file,
)
from stratajanus.index.binary_storage import (
    load_index as load_fixed_index,
)
from stratajanus.index.compressed_storage import (
    load_index as load_vb_index,
)
from stratajanus.index.storage import (
    load_index as load_json_index,
)
from stratajanus.retrieval.bm25 import BM25


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "scifact"
)

SPLIT_PATH = (
    PROJECT_ROOT
    / "configs"
    / "scifact_eval_split.json"
)

INDEX_OPTIONS = {
    "json": (
        PROJECT_ROOT / "data" / "indexes" / "scifact",
        load_json_index,
    ),
    "fixed32": (
        PROJECT_ROOT / "data" / "indexes" / "scifact-fixed32",
        load_fixed_index,
    ),
    "vb": (
        PROJECT_ROOT / "data" / "indexes" / "scifact-vb",
        load_vb_index,
    ),
}


def selected_judgments(
    split_name: str,
) -> tuple[dict[str, dict[str, int]], Path]:
    """Load qrels and select validation or official-test queries."""
    if split_name == "validation":
        qrels_path = DATA_DIR / "qrels" / "train.tsv"
        all_qrels = load_qrels(qrels_path)

        with SPLIT_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            split = json.load(file)

        if (
            split.get("dataset") != "scifact"
            or split.get("train_qrels_sha256")
            != sha256_file(qrels_path)
        ):
            raise ValueError(
                "Validation split does not match the "
                "current training qrels."
            )

        validation_ids = split.get(
            "validation_query_ids"
        )

        if (
            not isinstance(validation_ids, list)
            or not validation_ids
            or len(validation_ids)
            != len(set(validation_ids))
            or any(
                not isinstance(query_id, str)
                for query_id in validation_ids
            )
        ):
            raise ValueError(
                "Invalid validation query ID list."
            )

        if not set(validation_ids).issubset(all_qrels):
            raise ValueError(
                "Validation split references unknown queries."
            )

        return (
            {
                query_id: all_qrels[query_id]
                for query_id in sorted(validation_ids)
            },
            qrels_path,
        )

    qrels_path = DATA_DIR / "qrels" / "test.tsv"
    return load_qrels(qrels_path), qrels_path


def main():
    """Evaluate BM25 once and save aggregate and per-query metrics."""
    parser = argparse.ArgumentParser(
        description="Evaluate stratajanus BM25 on SciFact."
    )

    parser.add_argument(
        "--split",
        choices=["validation", "test"],
        default="validation",
    )

    parser.add_argument(
        "--format",
        choices=list(INDEX_OPTIONS),
        default="fixed32",
    )

    parser.add_argument(
        "--k1",
        type=float,
        default=1.2,
    )

    parser.add_argument(
        "--b",
        type=float,
        default=0.75,
    )

    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="New JSON report path; existing files are not overwritten.",
    )

    parser.add_argument(
        "--allow-test",
        action="store_true",
        help="Confirm an intentional evaluation on official test qrels.",
    )

    args = parser.parse_args()

    if args.split == "test" and not args.allow_test:
        parser.error(
            "Official test evaluation requires --allow-test. "
            "Tune on validation first."
        )

    if args.output.exists():
        raise FileExistsError(
            f"Report already exists: {args.output}"
        )

    index_directory, loader = INDEX_OPTIONS[args.format]

    if not index_directory.is_dir():
        raise FileNotFoundError(
            f"Saved index not found: {index_directory}"
        )

    queries_path = DATA_DIR / "queries.jsonl"

    queries = load_queries(queries_path)
    qrels, qrels_path = selected_judgments(args.split)

    if not qrels:
        raise ValueError("No queries with judgments were found.")

    index = loader(index_directory)

    # A relevant document missing from the corpus indicates an
    # incompatible dataset/index combination, not a retrieval failure.
    indexed_doc_ids = set(index.internal_to_external)

    for query_id, judgments in qrels.items():
        if query_id not in queries:
            raise ValueError(
                f"Missing query text for {query_id!r}."
            )

        relevant_ids = {
            doc_id
            for doc_id, relevance in judgments.items()
            if relevance > 0
        }

        if not relevant_ids:
            raise ValueError(
                f"Query {query_id!r} has no positive judgments."
            )

        missing = relevant_ids - indexed_doc_ids

        if missing:
            raise ValueError(
                f"Relevant documents for {query_id!r} "
                f"are absent from the index: {sorted(missing)}"
            )

    ranker = BM25(
        index,
        k1=args.k1,
        b=args.b,
    )

    per_query = {}
    query_details = {}

    for query_id in sorted(qrels):
        results = ranker.search(
            queries[query_id],
            top_k=100,
        )

        ranked_doc_ids = [
            result.doc_id
            for result in results
        ]

        metrics = evaluate_query(
            ranked_doc_ids,
            qrels[query_id],
        )

        per_query[query_id] = metrics

        query_details[query_id] = {
            "metrics": asdict(metrics),
            "ranked_doc_ids": ranked_doc_ids,
            "judged_relevant_count": sum(
                relevance > 0
                for relevance in qrels[query_id].values()
            ),
        }

    report = {
        "created_at_utc": (
            datetime.now(timezone.utc).isoformat()
        ),
        "dataset": "scifact",
        "split": args.split,
        "index_format": args.format,
        "index_directory": str(index_directory),
        "bm25": {
            "k1": args.k1,
            "b": args.b,
        },
        "evaluation_conventions": {
            "ndcg_cutoff": 10,
            "recall_cutoff": 100,
            "mrr_cutoff": 10,
            "relevant_if_score_greater_than": 0,
            "ndcg_gain": "2^relevance - 1",
            "unjudged_gain": 0,
            "queries_without_positive_judgments": "rejected",
        },
        "query_count": len(per_query),
        "mean_metrics": summarize_metrics(per_query),
        "per_query": query_details,
        "input_sha256": {
            "queries": sha256_file(queries_path),
            "qrels": sha256_file(qrels_path),
        },
    }

    if args.split == "validation":
        report["input_sha256"]["validation_split"] = (
            sha256_file(SPLIT_PATH)
        )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with args.output.open(
        "x",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")

    print(
        f"Evaluated {len(per_query)} "
        f"{args.split} queries."
    )

    for name, value in report["mean_metrics"].items():
        print(f"{name}: {value:.4f}")

    print(f"Saved report: {args.output}")


if __name__ == "__main__":
    main()