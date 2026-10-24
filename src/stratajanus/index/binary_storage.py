"""Store inverted indexes using fixed-width binary integers."""

import json
import struct
from pathlib import Path

from stratajanus.index.inverted import InvertedIndex
from stratajanus.index.validation import validate_index
from stratajanus.text.tokenizer import (
    save_tokenizer_config,
    verify_tokenizer_config,
)


FORMAT_NAME = "stratajanus-fixed32-inverted-index"
FORMAT_VERSION = 1

UINT32 = struct.Struct("<I")
POSTING = struct.Struct("<II")

MAX_UINT32 = (1 << 32) - 1


def _write_json(path: Path, value) -> None:
    """Write readable JSON metadata."""
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            value,
            file,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        file.write("\n")


def _read_json(path: Path):
    """Read a JSON metadata file."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _check_uint32(value: int, description: str) -> None:
    """Reject values that cannot be stored in four unsigned bytes."""
    if type(value) is not int or not 0 <= value <= MAX_UINT32:
        raise ValueError(
            f"{description} does not fit in an unsigned "
            f"32-bit integer: {value!r}"
        )

def save_index(index: InvertedIndex, directory: Path) -> None:
    """
    Save an index using fixed-width binary integers.

    Document IDs, term frequencies, and document lengths use
    unsigned 32-bit little-endian integers.

    Args:
        index: Complete in-memory inverted index.
        directory: New destination directory.

    Raises:
        FileExistsError: If the destination already exists.
        ValueError: If the index is invalid or contains values
            outside the supported integer range.

    A failed write may leave a partial directory. The manifest
    is written last.
    """
    directory = Path(directory)

    if directory.exists():
        raise FileExistsError(
            f"Index directory already exists: {directory}"
        )

    validate_index(index)

    for length in index.doc_lengths:
        _check_uint32(length, "Document length")

    for postings in index.postings.values():
        for internal_id, frequency in postings:
            _check_uint32(internal_id, "Internal document ID")
            _check_uint32(frequency, "Term frequency")

    directory.mkdir(parents=True, exist_ok=False)

    with (directory / "doc_lengths.bin").open("wb") as file:
        for length in index.doc_lengths:
            file.write(UINT32.pack(length))

    vocabulary = {}

    with (directory / "postings.bin").open("wb") as file:
        for term in sorted(index.postings):
            postings = index.postings[term]

            vocabulary[term] = {
                "offset": file.tell(),
                "document_frequency": len(postings),
            }

            for internal_id, frequency in postings:
                file.write(
                    POSTING.pack(internal_id, frequency)
                )

    _write_json(
        directory / "vocabulary.json",
        vocabulary,
    )

    _write_json(
        directory / "doc_ids.json",
        index.internal_to_external,
    )

    save_tokenizer_config(
        directory / "tokenizer_config.json"
    )

    _write_json(
        directory / "manifest.json",
        {
            "format": FORMAT_NAME,
            "format_version": FORMAT_VERSION,
            "document_count": index.document_count,
            "term_count": len(index.postings),
        },
    )


def load_index(directory: Path) -> InvertedIndex:
    """
    Load and validate a fixed-width binary index.

    The complete index is reconstructed in memory.

    Args:
        directory: Directory containing a saved binary index.

    Returns:
        An InvertedIndex with tuple-based posting lists.

    Raises:
        FileNotFoundError: If a required file is missing.
        ValueError: If metadata, tokenizer settings, binary layout,
            or index contents are inconsistent.
    """
    directory = Path(directory)

    required_files = [
        "manifest.json",
        "tokenizer_config.json",
        "vocabulary.json",
        "doc_ids.json",
        "doc_lengths.bin",
        "postings.bin",
    ]

    for name in required_files:
        path = directory / name

        if not path.is_file():
            raise FileNotFoundError(
                f"Required index file is missing: {path}"
            )

    manifest = _read_json(directory / "manifest.json")

    if not isinstance(manifest, dict):
        raise ValueError("Index manifest must be a JSON object.")

    if manifest.get("format") != FORMAT_NAME:
        raise ValueError("Unsupported binary index format.")

    if manifest.get("format_version") != FORMAT_VERSION:
        raise ValueError("Unsupported binary index format version.")

    verify_tokenizer_config(
        directory / "tokenizer_config.json"
    )

    document_ids = _read_json(directory / "doc_ids.json")
    vocabulary = _read_json(directory / "vocabulary.json")

    if not isinstance(document_ids, list):
        raise ValueError("Document IDs must be a JSON list.")

    if not isinstance(vocabulary, dict):
        raise ValueError("Vocabulary must be a JSON object.")

    document_count = len(document_ids)

    if manifest.get("document_count") != document_count:
        raise ValueError(
            "Document count does not match the manifest."
        )

    if manifest.get("term_count") != len(vocabulary):
        raise ValueError(
            "Term count does not match the manifest."
        )

    lengths_path = directory / "doc_lengths.bin"
    expected_length_bytes = document_count * UINT32.size

    if lengths_path.stat().st_size != expected_length_bytes:
        raise ValueError("Invalid document-length file size.")

    lengths_data = lengths_path.read_bytes()

    document_lengths = [
        length
        for (length,) in UINT32.iter_unpack(lengths_data)
    ]

    postings_path = directory / "postings.bin"
    postings_file_size = postings_path.stat().st_size

    postings = {}

    with postings_path.open("rb") as file:
        for term in sorted(vocabulary):
            entry = vocabulary[term]

            if not isinstance(entry, dict):
                raise ValueError(
                    f"Invalid vocabulary entry for {term!r}."
                )

            offset = entry.get("offset")
            document_frequency = entry.get(
                "document_frequency"
            )

            if (
                type(offset) is not int
                or offset != file.tell()
            ):
                raise ValueError(
                    f"Invalid posting offset for {term!r}."
                )

            if (
                type(document_frequency) is not int
                or not 1 <= document_frequency <= document_count
            ):
                raise ValueError(
                    f"Invalid document frequency for {term!r}."
                )

            byte_count = document_frequency * POSTING.size

            if offset + byte_count > postings_file_size:
                raise ValueError(
                    f"Truncated postings for {term!r}."
                )

            block = file.read(byte_count)

            if len(block) != byte_count:
                raise ValueError(
                    f"Truncated postings for {term!r}."
                )

            postings[term] = list(
                POSTING.iter_unpack(block)
            )

        if file.tell() != postings_file_size:
            raise ValueError(
                "Unexpected trailing data in postings.bin."
            )

    index = InvertedIndex(
        postings=postings,
        doc_lengths=document_lengths,
        internal_to_external=document_ids,
    )

    validate_index(index)

    return index