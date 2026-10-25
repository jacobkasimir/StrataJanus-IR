"""Compare SciFact vocabulary autocomplete implementations."""

import argparse
import gc
import importlib.util
import json
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path

from stratajanus.evaluation.performance import latency_summary
from stratajanus.index.binary_storage import load_index
from stratajanus.retrieval.autocomplete import (
    MarisaAutocomplete,
    SortedAutocomplete,
    TrieAutocomplete,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INDEX_DIR = (
    PROJECT_ROOT
    / "data"
    / "indexes"
    / "scifact-fixed32"
)

IMPLEMENTATIONS = {
    "trie": TrieAutocomplete,
    "sorted": SortedAutocomplete,
}

if importlib.util.find_spec("marisa_trie") is not None:
    IMPLEMENTATIONS["marisa"] = MarisaAutocomplete


def load_vocabulary() -> dict[str, int]:
    """Read document frequencies from the saved SciFact index."""
    index = load_index(INDEX_DIR)

    return {
        term: len(postings)
        for term, postings in index.postings.items()
    }


def make_prefixes(
    vocabulary: dict[str, int],
    count: int,
    seed: int,
) -> list[str]:
    """Create a fixed workload with narrow and broad prefixes."""
    terms = sorted(vocabulary)
    random_generator = random.Random(seed)

    selected = random_generator.sample(
        terms,
        k=min(count, len(terms)),
    )

    prefixes = [
        "",
        "p",
        "pro",
        "PRO",
        "zzzznotintheindex",
    ]

    for term in selected:
        prefixes.append(term[:1])
        prefixes.append(term[: min(3, len(term))])
        prefixes.append(term[: min(5, len(term))])

    # Remove duplicates while preserving the selected order.
    return list(dict.fromkeys(prefixes))


def measure_memory_in_child(name: str) -> dict | None:
    """Measure approximate RSS growth in a fresh process."""
    if importlib.util.find_spec("psutil") is None:
        return None

    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve()),
            "--memory-child",
            name,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return json.loads(completed.stdout)


def run_memory_child(name: str) -> None:
    """Build one implementation and report process RSS change."""
    import psutil

    vocabulary = load_vocabulary()
    gc.collect()

    process = psutil.Process(os.getpid())
    before = process.memory_info().rss

    autocomplete = IMPLEMENTATIONS[name](vocabulary)
    gc.collect()

    after = process.memory_info().rss

    # Keep the object alive until after the second measurement.
    assert autocomplete is not None

    print(json.dumps({
        "rss_before_bytes": before,
        "rss_after_bytes": after,
        "rss_delta_bytes": after - before,
    }))


def main():
    """Check equivalence and benchmark each autocomplete backend."""
    parser = argparse.ArgumentParser()

    parser.add_argument("--terms", type=int, default=100)
    parser.add_argument("--repeats", type=int, default=5)
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
            / "scifact-autocomplete.json"
        ),
    )

    # Internal option used to isolate memory measurements.
    parser.add_argument(
        "--memory-child",
        choices=["trie", "sorted", "marisa"],
    )

    args = parser.parse_args()

    if args.memory_child is not None:
        run_memory_child(args.memory_child)
        return

    if min(args.terms, args.repeats, args.top_k) <= 0:
        parser.error("--terms, --repeats, and --top-k must be positive.")

    if args.warmup_rounds < 0:
        parser.error("--warmup-rounds must be nonnegative.")

    if args.output.exists():
        raise FileExistsError(
            f"Benchmark report already exists: {args.output}"
        )

    vocabulary = load_vocabulary()
    prefixes = make_prefixes(
        vocabulary,
        args.terms,
        args.seed,
    )

    report = {
        "corpus": "scifact",
        "python": sys.version,
        "platform": platform.platform(),
        "vocabulary_size": len(vocabulary),
        "configuration": {
            "terms_sampled": args.terms,
            "actual_prefixes": len(prefixes),
            "repeats": args.repeats,
            "warmup_rounds": args.warmup_rounds,
            "top_k": args.top_k,
            "seed": args.seed,
        },
        "prefixes": prefixes,
        "implementations": {},
    }

    reference = None

    for name, implementation in IMPLEMENTATIONS.items():
        gc.collect()

        start = time.perf_counter_ns()
        autocomplete = implementation(vocabulary)
        build_ms = (
            time.perf_counter_ns() - start
        ) / 1_000_000

        # Check correctness outside the timed search loop.
        actual = {
            prefix: autocomplete.suggest(
                prefix,
                top_k=args.top_k,
            )
            for prefix in prefixes
        }

        if reference is None:
            reference = actual
        elif actual != reference:
            raise ValueError(
                f"{name} returns different suggestions."
            )

        for _ in range(args.warmup_rounds):
            for prefix in prefixes:
                autocomplete.suggest(
                    prefix,
                    top_k=args.top_k,
                )

        random_generator = random.Random(args.seed)
        samples = []

        for repeat in range(args.repeats):
            order = list(prefixes)
            random_generator.shuffle(order)

            for prefix in order:
                start = time.perf_counter_ns()

                results = autocomplete.suggest(
                    prefix,
                    top_k=args.top_k,
                )

                elapsed_ms = (
                    time.perf_counter_ns() - start
                ) / 1_000_000

                samples.append({
                    "prefix": prefix,
                    "repeat": repeat,
                    "latency_ms": elapsed_ms,
                    "result_count": len(results),
                })

        report["implementations"][name] = {
            "build_ms": build_ms,
            "query": {
                "summary": latency_summary([
                    sample["latency_ms"]
                    for sample in samples
                ]),
                "samples": samples,
            },
            "memory": measure_memory_in_child(name),
        }

        del autocomplete

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2, ensure_ascii=False)
        file.write("\n")

    print(
        f"{'Backend':<10} {'Build ms':>12} "
        f"{'p50 ms':>12} {'p95 ms':>12} "
        f"{'RSS delta':>14}"
    )

    for name, result in report["implementations"].items():
        summary = result["query"]["summary"]
        memory = result["memory"]

        memory_text = (
            f"{memory['rss_delta_bytes']:,}"
            if memory is not None
            else "not measured"
        )

        print(
            f"{name:<10} "
            f"{result['build_ms']:>12.3f} "
            f"{summary['p50_ms']:>12.3f} "
            f"{summary['p95_ms']:>12.3f} "
            f"{memory_text:>14}"
        )

    print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()