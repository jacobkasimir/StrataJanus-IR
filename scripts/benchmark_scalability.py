"""Coordinate isolated Wikipedia scalability benchmark trials."""

import argparse
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import psutil

from stratajanus.text.tokenizer import CONFIG


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "scripts" / "scalability_worker.py"


def sha256_file(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def run_worker(args, operation, mode, format_name, documents, index_dir, size):
    """Run one child process and parse its JSON result."""
    command = [
        sys.executable,
        str(WORKER),
        "--operation", operation,
        "--mode", mode,
        "--format", format_name,
        "--documents", str(documents),
        "--index-dir", str(index_dir),
        "--queries", str(args.queries.resolve()),
        "--expected-documents", str(size),
        "--query-repeats", str(args.query_repeats),
        "--top-k", str(args.top_k),
        "--seed", str(args.seed),
    ]

    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=args.timeout_seconds,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            f"Worker failed with code {completed.returncode}.\n"
            f"Command: {command}\n"
            f"stderr:\n{completed.stderr}\n"
            f"stdout:\n{completed.stdout}"
        )

    return json.loads(completed.stdout)


def print_summary(report):
    """Print medians across independent timing trials."""
    print(
        "\nDocuments  Format   Build s   Save s   Load s   "
        "Median p95 ms   Index MiB"
    )

    for size in report["configuration"]["sizes"]:
        for format_name in report["configuration"]["formats"]:
            runs = [
                run
                for run in report["runs"]
                if run["documents"] == size
                and run["format"] == format_name
                and run["mode"] == "timing"
            ]

            build_s = statistics.median(
                run["build"]["ingest_build"]["elapsed_ms"]
                for run in runs
            ) / 1000

            save_s = statistics.median(
                run["build"]["save"]["elapsed_ms"]
                for run in runs
            ) / 1000

            load_s = statistics.median(
                run["load"]["load"]["elapsed_ms"]
                for run in runs
            ) / 1000

            p95 = statistics.median(
                run["load"]["query"]["summary"]["p95_ms"]
                for run in runs
            )

            total_bytes = sum(
                runs[0]["build"]["files_bytes"].values()
            )

            print(
                f"{size:9,d}  {format_name:<7} "
                f"{build_s:8.2f} {save_s:8.2f} {load_s:8.2f} "
                f"{p95:15.3f} {total_bytes / (1024**2):11.2f}"
            )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=ROOT / "data" / "processed" / "wikipedia-20231101-en",
    )
    parser.add_argument(
        "--sizes", nargs="+", type=int, default=[10000, 50000, 100000]
    )
    parser.add_argument(
        "--formats", nargs="+", choices=["json", "fixed32", "vb"],
        default=["json", "fixed32", "vb"],
    )
    parser.add_argument(
        "--queries", type=Path,
        default=ROOT / "configs" / "wikipedia_queries.json",
    )
    parser.add_argument("--timing-repeats", type=int, default=3)
    parser.add_argument("--memory-repeats", type=int, default=1)
    parser.add_argument("--query-repeats", type=int, default=5)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("--hardware-notes", default="")
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    if (
        not args.sizes
        or min(args.sizes) <= 0
        or args.timing_repeats <= 0
        or args.memory_repeats < 0
        or args.query_repeats <= 0
        or args.top_k <= 0
        or args.timeout_seconds <= 0
    ):
        parser.error("Invalid counts, sizes, or timeout.")

    if args.output.exists():
        raise FileExistsError(f"Report exists: {args.output}")

    args.sizes = sorted(set(args.sizes))
    args.formats = list(dict.fromkeys(args.formats))

    manifest_path = args.corpus_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    query_rows = json.loads(args.queries.read_text(encoding="utf-8"))

    if (
        not isinstance(query_rows, list)
        or not query_rows
        or any(
            not isinstance(row, dict)
            or not isinstance(row.get("query_id"), str)
            or not row["query_id"]
            or not isinstance(row.get("text"), str)
            or not row["text"].strip()
            for row in query_rows
        )
    ):
        raise ValueError("Invalid query workload.")

    if len({row["query_id"] for row in query_rows}) != len(query_rows):
        raise ValueError("Query IDs must be unique.")

    inputs = {}

    for size in args.sizes:
        entry = manifest["subsets"].get(str(size))

        if entry is None or entry["documents"] != size:
            raise ValueError(f"Subset {size} is unavailable.")

        path = (args.corpus_root / entry["path"]).resolve()

        if sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Subset fingerprint mismatch: {path}")

        inputs[size] = path

    source_files = sorted(
        (ROOT / "src" / "stratajanus").rglob("*.py")
    ) + [WORKER, Path(__file__).resolve()]

    report = {
        "status": "running",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor(),
            "psutil_version": psutil.__version__,
            "hardware_notes": args.hardware_notes,
        },
        "configuration": {
            "sizes": args.sizes,
            "formats": args.formats,
            "timing_repeats": args.timing_repeats,
            "memory_repeats": args.memory_repeats,
            "query_repeats": args.query_repeats,
            "top_k": args.top_k,
            "seed": args.seed,
            "bm25": {"k1": 1.2, "b": 0.75},
            "build_scope": "JSONL reading, tokenization, indexing",
            "load_scope": "full decoding and validation",
            "query_scope": "warmed sequential BM25.search",
            "cache_state": "not cleared; files may be cached",
            "save_durability": "no explicit fsync",
            "memory": "separate runs; RSS sampled every 10 ms",
        },
        "tokenizer": asdict(CONFIG),
        "dataset_manifest": manifest,
        "workload": query_rows,
        "workload_sha256": sha256_file(args.queries),
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path)
            for path in source_files
        },
        "runs": [],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # Reserve this report path; later checkpoints update only this new file.
    with args.output.open("x", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    def checkpoint():
        with args.output.open("w", encoding="utf-8") as file:
            json.dump(report, file, indent=2, ensure_ascii=False)
            file.write("\n")

    temporary_parent = ROOT / "data" / "benchmark-tmp"
    temporary_parent.mkdir(parents=True, exist_ok=True)

    references = {}

    try:
        for size in args.sizes:
            for format_name in args.formats:
                for mode, repeats in [
                    ("timing", args.timing_repeats),
                    ("memory", args.memory_repeats),
                ]:
                    for repeat in range(repeats):
                        print(
                            f"{size:,} documents | {format_name} | "
                            f"{mode} | trial {repeat + 1}/{repeats}",
                            flush=True,
                        )

                        with tempfile.TemporaryDirectory(
                            prefix="scalability-",
                            dir=temporary_parent,
                        ) as temporary:
                            index_dir = Path(temporary) / "index"

                            build_result = run_worker(
                                args, "build", mode, format_name,
                                inputs[size], index_dir, size,
                            )

                            load_result = run_worker(
                                args, "load", mode, format_name,
                                inputs[size], index_dir, size,
                            )

                            if (
                                build_result["index_fingerprint"]
                                != load_result["index_fingerprint"]
                            ):
                                raise ValueError(
                                    "Saved index changed during round trip."
                                )

                            signature = (
                                load_result["index_fingerprint"],
                                load_result["query_signature"],
                            )

                            if size not in references:
                                references[size] = signature
                            elif references[size] != signature:
                                raise ValueError(
                                    "Formats or repetitions produced "
                                    "different indexes or rankings."
                                )

                            report["runs"].append({
                                "documents": size,
                                "format": format_name,
                                "mode": mode,
                                "repeat": repeat,
                                "build": build_result,
                                "load": load_result,
                            })

                        # Temporary index deletion is outside phase timers.
                        checkpoint()

    except BaseException as exc:
        report["status"] = "incomplete"
        report["error"] = f"{type(exc).__name__}: {exc}"
        checkpoint()
        raise

    report["status"] = "complete"
    checkpoint()
    print_summary(report)

    print(f"\nReport: {args.output}")


if __name__ == "__main__":
    main()