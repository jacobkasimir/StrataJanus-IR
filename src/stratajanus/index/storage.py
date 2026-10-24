"""Save and load stratajanus inverted indexes using JSON."""

import json
from pathlib import Path

from stratajanus.index.inverted import InvertedIndex
from stratajanus.text.tokenizer import (
    save_tokenizer_config,
    verify_tokenizer_config,
)


FORMAT_NAME = "stratajanus-inverted-index-json"
FORMAT_VERSION = 1

def _validate_index(index: InvertedIndex) -> None:
    """Check the structural consistency of a complete inverted index."""
    if not isinstance(index.postings, dict):
        raise ValueError("Index postings must be a dictionary.")

    if not isinstance(index.doc_lengths, list):
        raise ValueError("Document lengths must be a list.")

    if not isinstance(index.internal_to_external, list):
        raise ValueError("Document IDs must be a list.")

    document_ids = index.internal_to_external
    document_count = len(document_ids)

    if len(index.doc_lengths) != document_count:
        raise ValueError(
            "Document lengths and document IDs have different counts."
        )

    for doc_id in document_ids:
        if not isinstance(doc_id, str) or not doc_id:
            raise ValueError(
                "External document IDs must be nonempty strings."
            )

    if len(set(document_ids)) != document_count:
        raise ValueError("External document IDs must be unique.")

    for length in index.doc_lengths:
        if type(length) is not int or length < 0:
            raise ValueError(
                "Document lengths must be nonnegative integers."
            )

    reconstructed_lengths = [0] * document_count

    for term, postings in index.postings.items():
        if not isinstance(term, str) or not term:
            raise ValueError("Index terms must be nonempty strings.")

        if not isinstance(postings, list) or not postings:
            raise ValueError(
                f"Posting list for {term!r} must be a nonempty list."
            )

        previous_id = -1

        for posting in postings:
            if (
                not isinstance(posting, (tuple, list))
                or len(posting) != 2
            ):
                raise ValueError(
                    f"Invalid posting for term {term!r}."
                )

            internal_id, frequency = posting

            if (
                type(internal_id) is not int
                or not 0 <= internal_id < document_count
            ):
                raise ValueError(
                    f"Invalid document ID in postings for {term!r}."
                )

            if internal_id <= previous_id:
                raise ValueError(
                    f"Postings for {term!r} must have strictly "
                    "increasing document IDs."
                )

            if type(frequency) is not int or frequency <= 0:
                raise ValueError(
                    f"Invalid term frequency for {term!r}."
                )

            reconstructed_lengths[internal_id] += frequency
            previous_id = internal_id

    if reconstructed_lengths != index.doc_lengths:
        raise ValueError(
            "Posting frequencies do not match document lengths."
        )

def save_index(index: InvertedIndex, directory: Path) -> None:
    """
    Save a complete index to a new directory.

    Args:
        index: In-memory index to save.
        directory: Destination directory. It must not already exist.

    Raises:
        ValueError: If the index is structurally inconsistent.
        FileExistsError: If the destination already exists.

    The manifest is written last. A failed save may leave a partial
    directory that must be inspected before retrying.
    """
    directory = Path(directory)

    if directory.exists():
        raise FileExistsError(
            f"Index directory already exists: {directory}"
        )

    _validate_index(index)

    directory.mkdir(parents=True, exist_ok=False)

    payload = {
        "postings": index.postings,
        "doc_lengths": index.doc_lengths,
        "internal_to_external": index.internal_to_external,
    }

    with (directory / "index.json").open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        file.write("\n")

    save_tokenizer_config(
        directory / "tokenizer_config.json"
    )

    manifest = {
        "format": FORMAT_NAME,
        "format_version": FORMAT_VERSION,
        "document_count": index.document_count,
        "term_count": len(index.postings),
    }

    # Write this only after the index and tokenizer settings exist.
    with (directory / "manifest.json").open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(manifest, file, indent=2)
        file.write("\n")


def load_index(directory: Path) -> InvertedIndex:
    """
    Load and validate a saved JSON index.

    Args:
        directory: Directory containing the saved index files.

    Returns:
        A reconstructed InvertedIndex.

    Raises:
        FileNotFoundError: If a required file is missing.
        ValueError: If the format, tokenizer configuration, or index
            structure is incompatible or invalid.
    """
    directory = Path(directory)

    required_files = [
        directory / "manifest.json",
        directory / "tokenizer_config.json",
        directory / "index.json",
    ]

    for path in required_files:
        if not path.is_file():
            raise FileNotFoundError(
                f"Required index file is missing: {path}"
            )

    with (directory / "manifest.json").open(
        "r",
        encoding="utf-8",
    ) as file:
        manifest = json.load(file)

    if not isinstance(manifest, dict):
        raise ValueError("Index manifest must be a JSON object.")

    if manifest.get("format") != FORMAT_NAME:
        raise ValueError("Unsupported index format.")

    if manifest.get("format_version") != FORMAT_VERSION:
        raise ValueError("Unsupported index format version.")

    verify_tokenizer_config(
        directory / "tokenizer_config.json"
    )

    with (directory / "index.json").open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    try:
        index = InvertedIndex(
            postings={
                term: [tuple(posting) for posting in postings]
                for term, postings in payload["postings"].items()
            },
            doc_lengths=payload["doc_lengths"],
            internal_to_external=payload["internal_to_external"],
        )
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(
            "Saved index has an invalid structure."
        ) from exc

    _validate_index(index)

    if index.document_count != manifest.get("document_count"):
        raise ValueError(
            "Index document count does not match the manifest."
        )

    if len(index.postings) != manifest.get("term_count"):
        raise ValueError(
            "Index term count does not match the manifest."
        )

    return index