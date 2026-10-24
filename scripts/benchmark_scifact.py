"""Benchmark SciFact indexing, storage, loading, and BM25 queries."""

import argparse
import csv
import gc
import hashlib
import json
import os
import platform
import random
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict
from stratajanus.text.tokenizer import CONFIG

from stratajanus.evaluation.performance import benchmark_queries
from stratajanus.index.inverted import build_index
from stratajanus.retrieval.bm25 import BM25

from stratajanus.index.storage import (
    load_index as load_json,
    save_index as save_json,
)
from stratajanus.index.binary_storage import (
    load_index as load_fixed,
    save_index as save_fixed,
)
from stratajanus.index.compressed_storage import (
    load_index as load_vb,
    save_index as save_vb,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "scifact"

FORMATS = {
    "json": (save_json, load_json),
    "fixed32": (save_fixed, load_fixed),
    "vb": (save_vb, load_vb),
}

def read_jsonl(path: Path):
    """Yield decoded objects from nonblank JSONL lines."""
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path}, line {line_number}"
                ) from exc


def timed_call(function):
    """Run a zero-argument callable and return its result and elapsed ms."""
    start = time.perf_counter_ns()
    result = function()
    elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

    return result, elapsed_ms


def duration_summary(samples: list[float]) -> dict:
    """Summarize repeated build/save/load measurements."""
    return {
        "samples_ms": samples,
        "median_ms": statistics.median(samples),
        "min_ms": min(samples),
        "max_ms": max(samples),
    }


def sha256_file(path: Path) -> str:
    """Calculate a file fingerprint without loading it all at once."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def file_sizes(directory: Path) -> dict[str, int]:
    """Return logical file sizes relative to an index directory."""
    return {
        str(path.relative_to(directory)): path.stat().st_size
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }

def select_queries(count: int, seed: int) -> list[tuple[str, str]]:
    """Select a reproducible workload from canonical training qrels."""
    query_path = DATA_DIR / "queries.jsonl"
    qrels_path = DATA_DIR / "qrels" / "train.tsv"

    queries = {}

    for row in read_jsonl(query_path):
        query_id = row["query_id"]

        if query_id in queries:
            raise ValueError(f"Duplicate query ID: {query_id}")

        queries[query_id] = row["text"]

    with qrels_path.open(
        "r", encoding="utf-8", newline=""
    ) as file:
        reader = csv.DictReader(file, delimiter="\t")

        if "query_id" not in (reader.fieldnames or []):
            raise ValueError(
                "Expected canonical qrels with a query_id column."
            )

        training_ids = {
            row["query_id"]
            for row in reader
        }

    missing = training_ids - queries.keys()

    if missing:
        raise ValueError(
            f"Training judgments reference missing queries: {sorted(missing)}"
        )

    if not training_ids:
        raise ValueError("No training queries are available.")

    available = sorted(training_ids)
    generator = random.Random(seed)

    selected = generator.sample(
        available,
        k=min(count, len(available)),
    )

    return [
        (query_id, queries[query_id])
        for query_id in selected
    ]


def result_signature(ranker, queries, top_k):
    """Record ranked IDs and scores outside any timed measurement."""
    return {
        query_id: [
            (result.internal_id, result.doc_id, result.score)
            for result in ranker.search(query_text, top_k=top_k)
        ]
        for query_id, query_text in queries
    }

def main():
    """Run a reproducible single-process SciFact performance benchmark."""
    parser = argparse.ArgumentParser(
        description="Benchmark stratajanus on processed SciFact."
    )

    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--query-repeats", type=int, default=5)
    parser.add_argument("--index-repeats", type=int, default=3)
    parser.add_argument("--warmup-rounds", type=int, default=1)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            PROJECT_ROOT
            / "reports"
            / "benchmarks"
            / "scifact-baseline.json"
        ),
    )

    parser.add_argument(
        "--hardware-notes",
        default="",
        help="Optional CPU, RAM, storage, and power-mode description.",
    )

    args = parser.parse_args()

    if min(
        args.queries,
        args.query_repeats,
        args.index_repeats,
        args.top_k,
    ) <= 0:
        parser.error("Counts and top-k must be positive.")

    if args.warmup_rounds < 0:
        parser.error("--warmup-rounds must not be negative.")

    if args.output.exists():
        raise FileExistsError(
            f"Report already exists: {args.output}"
        )

    required_paths = [
        DATA_DIR / "documents.jsonl",
        DATA_DIR / "doc_ids.jsonl",
        DATA_DIR / "manifest.json",
        DATA_DIR / "queries.jsonl",
        DATA_DIR / "qrels" / "train.tsv",
    ]

    for path in required_paths:
        if not path.is_file():
            raise FileNotFoundError(
                f"Required processed dataset file is missing: {path}"
            )

    print("Reading corpus and selecting training queries...")

    documents, ingestion_ms = timed_call(
        lambda: list(read_jsonl(DATA_DIR / "documents.jsonl"))
    )

    queries = select_queries(args.queries, args.seed)

    with (DATA_DIR / "manifest.json").open(
        "r", encoding="utf-8"
    ) as file:
        dataset_manifest = json.load(file)

    if len(documents) != dataset_manifest["documents"]:
        raise ValueError("Corpus count differs from the dataset manifest.")

    expected_mapping = list(
        read_jsonl(DATA_DIR / "doc_ids.jsonl")
    )

    print("Measuring in-memory index construction...")

    build_times = []
    index = None

    for _ in range(args.index_repeats):
        index = None
        gc.collect()

        index, elapsed_ms = timed_call(
            lambda: build_index(documents)
        )
        build_times.append(elapsed_ms)

    actual_mapping = [
        {"internal_id": internal_id, "doc_id": doc_id}
        for internal_id, doc_id in enumerate(index.internal_to_external)
    ]

    if actual_mapping != expected_mapping:
        raise ValueError("Index IDs differ from the canonical ID mapping.")

    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "scifact",
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "logical_cpu_count": os.cpu_count(),
            "hardware_notes": args.hardware_notes,
        },
        "configuration": {
            "requested_queries": args.queries,
            "actual_queries": len(queries),
            "query_repeats": args.query_repeats,
            "index_repeats": args.index_repeats,
            "warmup_rounds": args.warmup_rounds,
            "top_k": args.top_k,
            "seed": args.seed,
            "bm25": {"k1": 1.2, "b": 0.75},
            "query_execution": "sequential, warmed, index in memory",
            "file_cache": "not cleared; indexes freshly written",
            "format_order": list(FORMATS),
            "save_durability": "file close; no explicit fsync",
        },
        "corpus": {
            "documents": index.document_count,
            "terms": len(index.postings),
            "average_document_length": index.average_document_length,
        },
        "workload": [
            {"query_id": query_id, "text": text}
            for query_id, text in queries
        ],
        "ingestion_ms": ingestion_ms,
        "build": duration_summary(build_times),
        "formats": {},
    }

    # Store benchmark indexes on the same filesystem as project data,
    # rather than relying on an OS temporary directory that might use RAM.
    temporary_parent = PROJECT_ROOT / "data" / "benchmark-tmp"
    temporary_parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="scifact-",
        dir=temporary_parent,
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        retained_paths = {}

        for name, (save, _) in FORMATS.items():
            print(f"Measuring {name} saving...")

            save_times = []

            for repeat in range(args.index_repeats):
                destination = temporary_root / f"{name}-{repeat}"

                gc.collect()
                _, elapsed_ms = timed_call(
                    lambda: save(index, destination)
                )
                save_times.append(elapsed_ms)

                if repeat == 0:
                    retained_paths[name] = destination
                else:
                    # Cleanup is deliberately outside the save timer.
                    shutil.rmtree(destination)

            sizes = file_sizes(retained_paths[name])

            report["formats"][name] = {
                "save": duration_summary(save_times),
                "files_bytes": sizes,
                "total_bytes": sum(sizes.values()),
            }

        # The original corpus and index are not needed during load/query tests.
        del index
        del documents
        gc.collect()

        reference_results = None

        for name, (_, load) in FORMATS.items():
            print(f"Measuring {name} loading and queries...")

            load_times = []
            loaded = None

            for _ in range(args.index_repeats):
                loaded = None
                gc.collect()

                loaded, elapsed_ms = timed_call(
                    lambda: load(retained_paths[name])
                )
                load_times.append(elapsed_ms)

            ranker, initialization_ms = timed_call(
                lambda: BM25(loaded, k1=1.2, b=0.75)
            )

            signature = result_signature(ranker, queries, args.top_k)

            if reference_results is None:
                reference_results = signature
            elif signature != reference_results:
                raise ValueError(
                    f"{name} produced different query results."
                )

            gc.collect()

            query_measurements = benchmark_queries(
                ranker,
                queries,
                top_k=args.top_k,
                repeats=args.query_repeats,
                warmup_rounds=args.warmup_rounds,
                seed=args.seed,
            )

            report["formats"][name].update({
                "load": duration_summary(load_times),
                "bm25_initialization_ms": initialization_ms,
                "query": query_measurements,
            })

            del ranker
            del loaded

    # Fingerprints are calculated outside all measured operations.
    report["input_sha256"] = {
        str(path.relative_to(PROJECT_ROOT)): sha256_file(path)
        for path in required_paths
    }

    source_paths = sorted(
        (PROJECT_ROOT / "src" / "stratajanus").rglob("*.py")
    )
    source_paths.append(Path(__file__).resolve())

    report["source_sha256"] = {
        str(path.relative_to(PROJECT_ROOT)): sha256_file(path)
        for path in source_paths
    }

    report["tokenizer_config"] = {
        # The saved configuration is generated by the existing tokenizer.
        # Import locally to avoid maintaining a second specification.
    }

    from dataclasses import asdict
    from stratajanus.text.tokenizer import CONFIG

    report["tokenizer_config"] = asdict(CONFIG)

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print("\nResults")
    print(
        f"{'Format':<10} {'Total bytes':>14} "
        f"{'Load ms':>12} {'Query p50':>12} {'Query p95':>12}"
    )

    for name, result in report["formats"].items():
        query = result["query"]["summary"]

        print(
            f"{name:<10} "
            f"{result['total_bytes']:>14,} "
            f"{result['load']['median_ms']:>12.3f} "
            f"{query['p50_ms']:>12.3f} "
            f"{query['p95_ms']:>12.3f}"
        )

    print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()