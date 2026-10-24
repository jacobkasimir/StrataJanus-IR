"""Persist indexes using document-ID gaps and variable-byte postings."""

import json
import struct
from pathlib import Path

from stratajanus.index.codecs import (
    MAX_UINT32,
    decode_uints,
    encode_uint,
)
from stratajanus.index.inverted import InvertedIndex
from stratajanus.index.validation import validate_index
from stratajanus.text.tokenizer import (
    save_tokenizer_config,
    verify_tokenizer_config,
)


FORMAT_NAME = "stratajanus-gap-uleb128-index"
FORMAT_VERSION = 1
UINT32 = struct.Struct("<I")


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
    """Read JSON metadata."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_index(index: InvertedIndex, directory: Path) -> None:
    """Save an index with gap-encoded, variable-byte postings.

    The destination must not exist. Document lengths remain fixed-width.
    A failed write may leave a partial directory.
    """
    directory = Path(directory)

    if directory.exists():
        raise FileExistsError(
            f"Index directory already exists: {directory}"
        )

    validate_index(index)

    if index.document_count > MAX_UINT32 + 1:
        raise ValueError("Document IDs exceed uint32 range.")

    if any(length > MAX_UINT32 for length in index.doc_lengths):
        raise ValueError("Document length exceeds uint32 range.")

    directory.mkdir(parents=True, exist_ok=False)

    with (directory / "doc_lengths.bin").open("wb") as file:
        for length in index.doc_lengths:
            file.write(UINT32.pack(length))

    vocabulary = {}

    with (directory / "postings.bin").open("wb") as file:
        for term in sorted(index.postings):
            offset = file.tell()
            previous_id = 0

            for internal_id, frequency in index.postings[term]:
                gap = internal_id - previous_id

                file.write(encode_uint(gap))
                file.write(encode_uint(frequency))

                previous_id = internal_id

            vocabulary[term] = {
                "offset": offset,
                "byte_length": file.tell() - offset,
                "document_frequency": len(index.postings[term]),
            }

    _write_json(directory / "vocabulary.json", vocabulary)
    _write_json(
        directory / "doc_ids.json",
        index.internal_to_external,
    )

    save_tokenizer_config(directory / "tokenizer_config.json")

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
    """Load compressed postings and reconstruct an in-memory index.

    Raises:
        FileNotFoundError: If required files are absent.
        ValueError: If metadata, encodings, or index structure are invalid.
    """
    directory = Path(directory)

    for name in (
        "manifest.json",
        "tokenizer_config.json",
        "vocabulary.json",
        "doc_ids.json",
        "doc_lengths.bin",
        "postings.bin",
    ):
        if not (directory / name).is_file():
            raise FileNotFoundError(
                f"Required index file is missing: {directory / name}"
            )

    manifest = _read_json(directory / "manifest.json")

    if (
        not isinstance(manifest, dict)
        or manifest.get("format") != FORMAT_NAME
        or manifest.get("format_version") != FORMAT_VERSION
    ):
        raise ValueError("Unsupported compressed index format.")

    verify_tokenizer_config(directory / "tokenizer_config.json")

    document_ids = _read_json(directory / "doc_ids.json")
    vocabulary = _read_json(directory / "vocabulary.json")

    if not isinstance(document_ids, list):
        raise ValueError("Document IDs must be a list.")

    if not isinstance(vocabulary, dict):
        raise ValueError("Vocabulary must be an object.")

    document_count = len(document_ids)

    if manifest.get("document_count") != document_count:
        raise ValueError("Document count does not match manifest.")

    if manifest.get("term_count") != len(vocabulary):
        raise ValueError("Term count does not match manifest.")

    lengths_path = directory / "doc_lengths.bin"

    if lengths_path.stat().st_size != document_count * UINT32.size:
        raise ValueError("Invalid document-length file size.")

    document_lengths = [
        length
        for (length,) in UINT32.iter_unpack(lengths_path.read_bytes())
    ]

    postings_path = directory / "postings.bin"
    file_size = postings_path.stat().st_size
    postings = {}

    with postings_path.open("rb") as file:
        for term in sorted(vocabulary):
            entry = vocabulary[term]

            if not isinstance(entry, dict):
                raise ValueError("Invalid vocabulary entry.")

            offset = entry.get("offset")
            byte_length = entry.get("byte_length")
            frequency = entry.get("document_frequency")

            if type(offset) is not int or offset != file.tell():
                raise ValueError("Invalid posting offset.")

            if (
                type(frequency) is not int
                or not 1 <= frequency <= document_count
            ):
                raise ValueError("Invalid document frequency.")

            # Each posting contains two integers, each taking 1–5 bytes.
            if (
                type(byte_length) is not int
                or not 2 * frequency <= byte_length <= 10 * frequency
            ):
                raise ValueError("Invalid posting byte length.")

            if offset + byte_length > file_size:
                raise ValueError("Truncated compressed postings.")

            block = file.read(byte_length)

            if len(block) != byte_length:
                raise ValueError("Truncated compressed postings.")

            integers = decode_uints(block)

            if len(integers) != 2 * frequency:
                raise ValueError("Decoded posting count is incorrect.")

            decoded_postings = []
            previous_id = 0

            for position in range(0, len(integers), 2):
                gap = integers[position]
                term_frequency = integers[position + 1]

                internal_id = previous_id + gap

                if internal_id > MAX_UINT32:
                    raise ValueError("Decoded document ID exceeds uint32.")

                decoded_postings.append(
                    (internal_id, term_frequency)
                )
                previous_id = internal_id

            postings[term] = decoded_postings

        if file.tell() != file_size:
            raise ValueError("Unexpected trailing posting data.")

    index = InvertedIndex(
        postings=postings,
        doc_lengths=document_lengths,
        internal_to_external=document_ids,
    )

    validate_index(index)

    return index