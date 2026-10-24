"""Build and save an uncompressed SciFact inverted index."""

import json
from pathlib import Path

from stratajanus.index.inverted import build_index
from stratajanus.index.storage import save_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data" / "processed" / "scifact"
INDEX_DIR = PROJECT_ROOT / "data" / "indexes" / "scifact"


def read_jsonl(path: Path):
    """Yield JSON objects from nonempty lines."""
    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path}, line {line_number}"
                ) from exc

            yield row


def main():
    """Build SciFact, verify its IDs, and save the index."""
    if INDEX_DIR.exists():
        raise FileExistsError(
            f"Index already exists: {INDEX_DIR}\n"
            "Use the search script to query it."
        )

    documents_path = DATA_DIR / "documents.jsonl"
    mapping_path = DATA_DIR / "doc_ids.jsonl"
    manifest_path = DATA_DIR / "manifest.json"

    for path in (
        documents_path,
        mapping_path,
        manifest_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(
                f"Missing processed dataset file: {path}"
            )

    print("Building SciFact index...")

    index = build_index(read_jsonl(documents_path))

    with manifest_path.open("r", encoding="utf-8") as file:
        dataset_manifest = json.load(file)

    if index.document_count != dataset_manifest["documents"]:
        raise ValueError(
            "Index document count differs from the dataset manifest."
        )

    saved_mapping = list(read_jsonl(mapping_path))

    generated_mapping = [
        {
            "internal_id": internal_id,
            "doc_id": doc_id,
        }
        for internal_id, doc_id in enumerate(
            index.internal_to_external
        )
    ]

    if saved_mapping != generated_mapping:
        raise ValueError(
            "Index document IDs differ from doc_ids.jsonl."
        )

    save_index(index, INDEX_DIR)

    print(f"Documents: {index.document_count:,}")
    print(f"Distinct terms: {len(index.postings):,}")
    print(f"Saved index to: {INDEX_DIR}")


if __name__ == "__main__":
    main()