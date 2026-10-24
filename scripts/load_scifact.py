"""Search a saved SciFact index using BM25."""

import argparse
import json
from pathlib import Path

from stratajanus.index.storage import load_index
from stratajanus.retrieval.bm25 import BM25


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INDEX_DIR = PROJECT_ROOT / "data" / "indexes" / "scifact"

DOCUMENTS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "scifact"
    / "documents.jsonl"
)


def find_titles(doc_ids: set[str]) -> dict[str, str]:
    """
    Look up result titles in the processed corpus.

    Returns an empty mapping if the corpus file is unavailable.
    This affects display only, not ranking.
    """
    if not doc_ids or not DOCUMENTS_PATH.is_file():
        return {}

    titles = {}

    with DOCUMENTS_PATH.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            document = json.loads(line)
            doc_id = document["doc_id"]

            if doc_id in doc_ids:
                titles[doc_id] = document["title"]

            if len(titles) == len(doc_ids):
                break

    return titles


def main():
    """Load an existing index and print ranked search results."""
    parser = argparse.ArgumentParser(
        description="Search SciFact using a saved stratajanus index."
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

    args = parser.parse_args()

    if not INDEX_DIR.is_dir():
        raise FileNotFoundError(
            f"No saved index found at: {INDEX_DIR}\n"
            "Run: python scripts/build_scifact_index.py"
        )

    print("Loading saved index...")
    index = load_index(INDEX_DIR)

    ranker = BM25(index)
    results = ranker.search(args.query, top_k=args.top_k)

    titles = find_titles({
        result.doc_id
        for result in results
    })

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