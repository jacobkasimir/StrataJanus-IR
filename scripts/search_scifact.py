"""Search the processed SciFact collection using in-memory BM25 ranking."""

import argparse
import json
from pathlib import Path

from stratajanus.index.inverted import build_index
from stratajanus.retrieval.bm25 import BM25


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOCUMENTS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "scifact"
    / "documents.jsonl"
)


def read_documents(path: Path):
    """Yield nonblank JSONL document values in source order.

    Args:
        path: UTF-8 JSON Lines file containing processed documents.

    Each yielded value is decoded JSON for the index builder.

    Raises:
        FileNotFoundError: If the file is missing.
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


def main():
    """Parse a query, build the SciFact index, and print ranked results.

    The command accepts one query argument and an optional ``--top-k`` count.
    It rebuilds the full in-memory index for each invocation and uses result
    internal IDs to retrieve the corresponding source documents for display.

    Raises:
        SystemExit: For command-line parsing errors.
        FileNotFoundError: If the processed SciFact corpus is not present.

    Side effects:
        Writes progress and ranked result details to standard output.
    """
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

    args = parser.parse_args()

    if not DOCUMENTS_PATH.is_file():
        raise FileNotFoundError(
            f"Missing processed corpus: {DOCUMENTS_PATH}"
        )

    # SciFact is small enough to retain the documents for display.
    documents = list(read_documents(DOCUMENTS_PATH))

    print(f"Building index for {len(documents):,} documents...")

    index = build_index(documents)
    ranker = BM25(index)

    results = ranker.search(
        args.query,
        top_k=args.top_k,
    )

    print(f"\nQuery: {args.query}")
    print(f"Results returned: {len(results)}\n")

    for rank, result in enumerate(results, start=1):
        document = documents[result.internal_id]

        print(
            f"{rank}. {result.doc_id} "
            f"| BM25 score: {result.score:.4f}"
        )
        print(f"   {document['title']}")
        print()


if __name__ == "__main__":
    main()
"""Search the processed SciFact collection using in-memory BM25 ranking."""
