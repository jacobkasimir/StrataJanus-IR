"""Prepare deterministic, nested Wikipedia subsets for benchmarking."""

import argparse
import hashlib
import json
from contextlib import ExitStack
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DATASET_NAME = "wikimedia/wikipedia"
DATASET_CONFIG = "20231101.en"

DEFAULT_OUTPUT = (
    ROOT / "data" / "processed" / "wikipedia-20231101-en"
)


def write_subsets(rows, sizes, output_root, source):
    """Write nested canonical subsets from source records.

    Empty document bodies are skipped. Eligible records are retained
    in source order. Existing output directories are never overwritten.

    A failed preparation may leave partial output. The top-level
    manifest is written only after all requested subsets are complete.
    """
    output_root = Path(output_root)
    sizes = sorted(set(sizes))

    if not sizes or any(
        type(size) is not int or size <= 0
        for size in sizes
    ):
        raise ValueError("Subset sizes must be positive integers.")

    if output_root.exists():
        raise FileExistsError(
            f"Output directory already exists: {output_root}"
        )

    output_root.mkdir(parents=True)

    hashes = {
        size: hashlib.sha256()
        for size in sizes
    }

    retained = 0
    skipped_empty = 0
    seen_ids = set()

    with ExitStack() as stack:
        files = {}

        for size in sizes:
            directory = output_root / str(size)
            directory.mkdir()

            files[size] = stack.enter_context(
                (directory / "documents.jsonl").open("xb")
            )

        for row in rows:
            title = row.get("title")
            text = row.get("text")
            source_id = row.get("id")

            if (
                not isinstance(title, str)
                or not isinstance(text, str)
                or source_id is None
            ):
                raise ValueError("Unexpected Wikipedia record schema.")

            if not text.strip():
                skipped_empty += 1
                continue

            doc_id = "wikipedia-en:" + str(source_id)

            if doc_id in seen_ids:
                raise ValueError(
                    f"Duplicate source document ID: {doc_id}"
                )

            seen_ids.add(doc_id)

            document = {
                "doc_id": doc_id,
                "title": title,
                "text": text,
                "metadata": {
                    "source": "wikipedia",
                    "url": row.get("url", ""),
                },
            }

            encoded = (
                json.dumps(
                    document,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")

            for size in sizes:
                if retained < size:
                    files[size].write(encoded)
                    hashes[size].update(encoded)

            retained += 1

            if retained >= sizes[-1]:
                break

    if retained < sizes[-1]:
        raise ValueError(
            f"Source ended after {retained} eligible documents; "
            f"{sizes[-1]} were requested."
        )

    manifest = {
        "source": source,
        "selection": "first eligible records in pinned source order",
        "empty_bodies_skipped": skipped_empty,
        "subsets": {
            str(size): {
                "documents": size,
                "path": f"{size}/documents.jsonl",
                "sha256": hashes[size].hexdigest(),
            }
            for size in sizes
        },
    }

    with (output_root / "manifest.json").open(
        "x", encoding="utf-8"
    ) as file:
        json.dump(manifest, file, indent=2, ensure_ascii=False)
        file.write("\n")

    return manifest


def main():
    """Resolve a dataset revision and stream the requested subsets."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[10000, 50000, 100000],
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    parser.add_argument(
        "--revision",
        default=None,
        help="Optional existing dataset revision to reproduce.",
    )

    args = parser.parse_args()

    if args.output_root.exists():
        raise FileExistsError(
            f"Output already exists: {args.output_root}"
        )

    # Imports stay here so synthetic preparation tests need no network
    # and do not require the dataset download packages.
    import datasets
    from datasets import load_dataset
    from huggingface_hub import HfApi

    information = HfApi().dataset_info(
        DATASET_NAME,
        revision=args.revision,
    )

    revision = information.sha

    if not revision:
        raise ValueError("Could not resolve a dataset revision.")

    print(f"Dataset: {DATASET_NAME}")
    print(f"Configuration: {DATASET_CONFIG}")
    print(f"Pinned revision: {revision}")

    rows = load_dataset(
        DATASET_NAME,
        DATASET_CONFIG,
        split="train",
        revision=revision,
        streaming=True,
    )

    manifest = write_subsets(
        rows,
        args.sizes,
        args.output_root,
        source={
            "dataset": DATASET_NAME,
            "configuration": DATASET_CONFIG,
            "revision": revision,
            "datasets_version": datasets.__version__,
        },
    )

    for size, details in manifest["subsets"].items():
        print(f"{size} documents: {details['sha256']}")

    print(f"Prepared data: {args.output_root}")


if __name__ == "__main__":
    main()