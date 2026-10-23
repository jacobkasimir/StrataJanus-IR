"""Build and validate the processed SciFact index in memory."""

import json
from pathlib import Path

from stratajanus.index.inverted import build_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed" / "scifact"


def read_jsonl(path: Path):
    """Yield nonblank JSONL objects in file order.

    Args:
        path: UTF-8 JSON Lines file.

    Each yielded value is decoded JSON; the index builder validates document
    records.

    Raises:
        FileNotFoundError: If the file is absent.
        ValueError: If a nonblank line contains malformed JSON.
    """
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path}, line {line_number}"
                ) from exc


def main():
    """Build an in-memory index and validate it against the processed manifest.

    Reads ``documents.jsonl``, ``doc_ids.jsonl``, and ``manifest.json``;
    prints index statistics and sample postings. Does not persist the index.

    Raises:
        FileNotFoundError: If any required processed file is missing.
        ValueError: If counts or internal/external ID mappings disagree.
    """
    documents_path = DATA_DIR / "documents.jsonl"
    mapping_path = DATA_DIR / "doc_ids.jsonl"
    manifest_path = DATA_DIR / "manifest.json"

    for path in (documents_path, mapping_path, manifest_path):
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing {path}. Complete Step 4 first."
            )

    # build_index accepts an iterable, so it can consume the
    # documents produced by read_jsonl one at a time.
    index = build_index(read_jsonl(documents_path))

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    expected_count = manifest["documents"]

    if index.document_count != expected_count:
        raise ValueError(
            f"Document count mismatch: index has "
            f"{index.document_count}, manifest says {expected_count}"
        )

    # Step 4 assigned internal IDs in corpus-file order.
    # Confirm that build_index assigned exactly the same IDs.
    mapping_count = 0

    for mapping in read_jsonl(mapping_path):
        expected_internal_id = mapping_count
        actual_internal_id = mapping["internal_id"]

        if actual_internal_id != expected_internal_id:
            raise ValueError(
                f"Mapping entry {mapping_count} has internal ID "
                f"{actual_internal_id}, expected {expected_internal_id}"
            )

        if expected_internal_id >= index.document_count:
            raise ValueError(
                "ID mapping contains more documents than the index"
            )

        expected_doc_id = mapping["doc_id"]
        actual_doc_id = index.internal_to_external[
            expected_internal_id
        ]

        if actual_doc_id != expected_doc_id:
            raise ValueError(
                f"ID mismatch at position {expected_internal_id}: "
                f"index has {actual_doc_id!r}, "
                f"mapping has {expected_doc_id!r}"
            )

        mapping_count += 1

    if mapping_count != index.document_count:
        raise ValueError(
            f"ID mapping has {mapping_count} documents; "
            f"index has {index.document_count}"
        )

    print("SciFact index checks passed.")
    print(f"Documents: {index.document_count:,}")
    print(f"Distinct terms: {len(index.postings):,}")
    print(
        "Average document length: "
        f"{index.average_document_length:.2f} tokens"
    )

    print("\nExample terms:")
    for term in ("science", "evidence", "protein"):
        postings = index.postings.get(term, [])
        print(
            f"  {term!r}: {len(postings)} documents; "
            f"first five postings: {postings[:5]}"
        )


if __name__ == "__main__":
    main()
"""Build and validate the processed SciFact index in memory."""
