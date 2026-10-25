"""Suggest SciFact vocabulary terms for a typed prefix."""

import argparse
from pathlib import Path

from stratajanus.index.binary_storage import load_index
from stratajanus.retrieval.autocomplete import TrieAutocomplete


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INDEX_DIR = (
    PROJECT_ROOT
    / "data"
    / "indexes"
    / "scifact-fixed32"
)


def main():
    """Load SciFact vocabulary and display trie suggestions."""
    parser = argparse.ArgumentParser(
        description="Autocomplete SciFact vocabulary terms."
    )

    parser.add_argument("prefix")
    parser.add_argument("--top-k", type=int, default=10)

    args = parser.parse_args()

    if not INDEX_DIR.is_dir():
        raise FileNotFoundError(
            f"Missing index: {INDEX_DIR}\n"
            "Build the JSON index and convert it to fixed32 first."
        )

    index = load_index(INDEX_DIR)

    vocabulary = {
        term: len(postings)
        for term, postings in index.postings.items()
    }

    autocomplete = TrieAutocomplete(vocabulary)

    for suggestion in autocomplete.suggest(
        args.prefix,
        top_k=args.top_k,
    ):
        print(
            f"{suggestion.term}\t"
            f"df={suggestion.document_frequency}"
        )


if __name__ == "__main__":
    main()