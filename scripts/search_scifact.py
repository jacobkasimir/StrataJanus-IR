"""Search SciFact using a saved stratajanus index and BM25 ranking."""

import argparse
import json
from pathlib import Path

from stratajanus.index.binary_storage import (
    load_index as load_binary_index,
)
from stratajanus.index.storage import (
    load_index as load_json_index,
)
from stratajanus.retrieval.bm25 import BM25


PROJECT_ROOT = Path(__file__).resolve().parents[1]

JSON_INDEX_DIR = (
    PROJECT_ROOT / "data" / "indexes" / "scifact"
)

BINARY_INDEX_DIR = (
    PROJECT_ROOT / "data" / "indexes" / "scifact-fixed32"
)

DOCUMENTS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "scifact"
    / "documents.jsonl"
)


def read_documents(path: Path):
    """Yield processed SciFact documents in their original order.

    Args:
        path: UTF-8 JSONL file containing canonical documents.

    Yields:
        One decoded document dictionary per nonblank line.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If a nonblank line contains malformed JSON.
    """
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                document = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path}, line {line_number}"
                ) from exc

            yield document


def find_titles(doc_ids: set[str]) -> dict[str, str]:
    """Find titles for the external document IDs in search results.

    Titles are read from the processed corpus only for display.
    This function does not build an index or affect BM25 scores.

    Args:
        doc_ids: External document IDs whose titles are needed.

    Returns:
        A mapping from found document IDs to titles. Returns an empty
        mapping if the corpus file is unavailable.
    """
    if not doc_ids or not DOCUMENTS_PATH.is_file():
        return {}

    titles = {}

    for document in read_documents(DOCUMENTS_PATH):
        doc_id = document["doc_id"]

        if doc_id in doc_ids:
            titles[doc_id] = document["title"]

        if len(titles) == len(doc_ids):
            break

    return titles


def main():
    """Load a saved index, run BM25, and display ranked SciFact results."""
    parser = argparse.ArgumentParser(
        description="Search SciFact using stratajanus BM25."
    )

    parser.add_argument(
        "query",
        help="Search query. Put multiword queries in quotes.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Maximum number of results.",
    )

    parser.add_argument(
        "--format",
        choices=["json", "fixed32"],
        default="json",
        help="Saved index format to load.",
    )

    args = parser.parse_args()

    if args.format == "fixed32":
        index_directory = BINARY_INDEX_DIR
        loader = load_binary_index
        build_command = "python scripts/convert_index_to_binary.py"
    else:
        index_directory = JSON_INDEX_DIR
        loader = load_json_index
        build_command = "python scripts/build_scifact_index.py"

    if not index_directory.is_dir():
        raise FileNotFoundError(
            f"No saved index found at: {index_directory}\n"
            f"Run: {build_command}"
        )

    print(f"Loading {args.format} index...")
    index = loader(index_directory)

    ranker = BM25(index)

    results = ranker.search(
        args.query,
        top_k=args.top_k,
    )

    titles = find_titles(
        {result.doc_id for result in results}
    )

    print(f"\nQuery: {args.query}")
    print(f"Results returned: {len(results)}\n")

    for rank, result in enumerate(results, start=1):
        print(
            f"{rank}. {result.doc_id} "
            f"| BM25 score: {result.score:.4f}"
        )

        title = titles.get(result.doc_id)

        if title:
            print(f"   {title}")

        print()


if __name__ == "__main__":
    main()