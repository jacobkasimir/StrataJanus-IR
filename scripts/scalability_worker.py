"""Execute one isolated scalability benchmark operation."""

import argparse
import gc
import hashlib
import json
import os
import threading
import time
from pathlib import Path

import psutil

from stratajanus.evaluation.performance import benchmark_queries
from stratajanus.index.inverted import build_index
from stratajanus.retrieval.bm25 import BM25
from stratajanus.text.tokenizer import tokenize

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


FORMATS = {
    "json": (save_json, load_json),
    "fixed32": (save_fixed, load_fixed),
    "vb": (save_vb, load_vb),
}


def read_documents(path):
    """Yield canonical documents without retaining the corpus text."""
    with Path(path).open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path}, line {line_number}"
                ) from exc


def measure(function, mode):
    """Measure elapsed time OR approximate peak RSS for one operation."""
    gc.collect()

    if mode == "timing":
        start = time.perf_counter_ns()
        result = function()

        return result, {
            "elapsed_ms": (
                time.perf_counter_ns() - start
            ) / 1_000_000
        }

    process = psutil.Process(os.getpid())
    baseline = process.memory_info().rss
    peak = [baseline]
    stop = threading.Event()

    def sample():
        while not stop.wait(0.01):
            peak[0] = max(
                peak[0],
                process.memory_info().rss,
            )

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()

    try:
        result = function()
    finally:
        stop.set()
        sampler.join()
        peak[0] = max(
            peak[0],
            process.memory_info().rss,
        )

    return result, {
        "rss_before_bytes": baseline,
        "sampled_peak_rss_bytes": peak[0],
        "rss_after_bytes": process.memory_info().rss,
        "sampling_interval_ms": 10,
    }


def index_fingerprint(index):
    """Hash logical index contents independently of disk encoding."""
    digest = hashlib.sha256()

    def update(value):
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        digest.update(encoded)
        digest.update(b"\n")

    update(index.internal_to_external)
    update(index.doc_lengths)

    for term in sorted(index.postings):
        update([term, index.postings[term]])

    return digest.hexdigest()


def query_signature(ranker, queries, top_k):
    """Hash complete ranked results without rounding BM25 scores."""
    digest = hashlib.sha256()

    for query_id, text in queries:
        results = ranker.search(text, top_k=top_k)

        value = [
            query_id,
            [
                [result.doc_id, result.score.hex()]
                for result in results
            ],
        ]

        digest.update(
            json.dumps(value, ensure_ascii=False).encode("utf-8")
        )
        digest.update(b"\n")

    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--operation", choices=["build", "load"], required=True)
    parser.add_argument("--mode", choices=["timing", "memory"], required=True)
    parser.add_argument("--format", choices=list(FORMATS), required=True)
    parser.add_argument("--documents", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--expected-documents", type=int, required=True)
    parser.add_argument("--query-repeats", type=int, default=5)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()
    save, load = FORMATS[args.format]

    result = {
        "operation": args.operation,
        "mode": args.mode,
        "format": args.format,
    }

    if args.operation == "build":
        index, result["ingest_build"] = measure(
            lambda: build_index(read_documents(args.documents)),
            args.mode,
        )

        if index.document_count != args.expected_documents:
            raise ValueError("Unexpected indexed document count.")

        _, result["save"] = measure(
            lambda: save(index, args.index_dir),
            args.mode,
        )

        result["document_count"] = index.document_count
        result["term_count"] = len(index.postings)

        # Integrity work is deliberately outside measured phases.
        result["index_fingerprint"] = index_fingerprint(index)

        result["files_bytes"] = {
            str(path.relative_to(args.index_dir)): path.stat().st_size
            for path in sorted(args.index_dir.rglob("*"))
            if path.is_file()
        }

    else:
        index, result["load"] = measure(
            lambda: load(args.index_dir),
            args.mode,
        )

        if index.document_count != args.expected_documents:
            raise ValueError("Unexpected loaded document count.")

        result["index_fingerprint"] = index_fingerprint(index)

        ranker, result["bm25_initialization"] = measure(
            lambda: BM25(index, k1=1.2, b=0.75),
            args.mode,
        )

        rows = json.loads(args.queries.read_text(encoding="utf-8"))
        queries = [
            (row["query_id"], row["text"])
            for row in rows
        ]

        result["query_signature"] = query_signature(
            ranker, queries, args.top_k
        )

        result["query_postings_visited"] = {
            query_id: sum(
                len(index.postings.get(term, []))
                for term in set(tokenize(text))
            )
            for query_id, text in queries
        }

        if args.mode == "timing":
            gc.collect()

            result["query"] = benchmark_queries(
                ranker,
                queries,
                top_k=args.top_k,
                repeats=args.query_repeats,
                warmup_rounds=1,
                seed=args.seed,
            )
        else:
            # query_signature already performed an untimed search pass.
            def run_query_batch():
                for _, text in queries:
                    ranker.search(text, top_k=args.top_k)

            _, result["query_batch"] = measure(
                run_query_batch,
                args.mode,
            )

    # The parent expects exactly one JSON object on stdout.
    print(json.dumps(result))


if __name__ == "__main__":
    main()