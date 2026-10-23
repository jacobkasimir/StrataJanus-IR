"""Validate BEIR SciFact files and convert them to stratajanus JSONL/TSV."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_DIR = PROJECT_ROOT / "data" / "raw" / "scifact"

OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "scifact"

SCHEMA_VERSION = 1

def read_jsonl(path):
    """Read nonblank JSON Lines records with their source line numbers.

    Args:
        path (Path): UTF-8 JSONL file to read.

    Each yielded pair contains the source line number and decoded JSON object.

    Raises:
        ValueError: If a nonblank line is invalid JSON or is not a JSON object.
    """
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

            if not isinstance(row, dict):
                raise ValueError(
                    f"Expected a JSON object in {path}, "
                    f"line {line_number}"
                )

            yield line_number, row


def require_id(row, field, location):
    """Return a required nonempty string identifier from a record.

    Args:
        row (dict[str, Any]): Record containing the identifier.
        field (str): Identifier field name.
        location (str): Source location used in validation errors.

    The validated identifier is returned unchanged.

    Raises:
        ValueError: If the field is missing, not a string, or blank.
    """
    value = row.get(field)

    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            f"{location}: '{field}' must be a nonempty string"
        )

    return value


def require_text(row, field, location, default=None):
    """Return a string field, using a default only when it is absent.

    Args:
        row (dict[str, Any]): Record containing the text field.
        field (str): Text field name.
        location (str): Source location used in validation errors.
        default (str | None): Value to use when the field is absent.

    The selected string value is returned unchanged.

    Raises:
        ValueError: If the selected value is not a string.
    """
    value = row.get(field, default)

    if not isinstance(value, str):
        raise ValueError(
            f"{location}: '{field}' must be a string"
        )

    return value


def prepare_metadata(row, location):
    """Copy a record's metadata and mark it as originating from SciFact.

    Args:
        row (dict[str, Any]): Input record containing optional metadata.
        location (str): Source location used in validation errors.

    The returned metadata copy has its source set to ``scifact``.

    Raises:
        ValueError: If metadata is not a JSON object.
    """
    metadata = row.get("metadata", {})

    if not isinstance(metadata, dict):
        raise ValueError(
            f"{location}: 'metadata' must be an object"
        )

    return {
        **metadata,
        "source": "scifact",
    }


def write_jsonl_row(file, row):
    """Serialize one object as a UTF-8-compatible JSON Lines record.

    Args:
        file (TextIO): Writable text stream.
        row (dict[str, Any]): Object to serialize.

    Side effects:
        Writes one JSON record and newline to the supplied open text stream;
        this helper does not open or close files itself.
    """
    file.write(
        json.dumps(row, ensure_ascii=False) + "\n"
    )

def convert_documents():
    """Convert the raw SciFact corpus and create its external ID mapping.

    Returns the set of document IDs and the number of empty documents.

    Raises:
        ValueError: If a record is invalid or contains a duplicate document ID.
    """
    input_path = RAW_DIR / "corpus.jsonl"
    documents_path = OUTPUT_DIR / "documents.jsonl"
    mapping_path = OUTPUT_DIR / "doc_ids.jsonl"

    seen_ids = set()
    empty_documents = 0

    with (
        documents_path.open("w", encoding="utf-8") as documents_file,
        mapping_path.open("w", encoding="utf-8") as mapping_file,
    ):
        for line_number, row in read_jsonl(input_path):
            location = f"{input_path}:{line_number}"

            doc_id = require_id(row, "_id", location)
            title = require_text(row, "title", location, default="")
            text = require_text(row, "text", location)

            if doc_id in seen_ids:
                raise ValueError(
                    f"{location}: duplicate document ID '{doc_id}'"
                )

            internal_id = len(seen_ids)
            seen_ids.add(doc_id)

            if not title.strip() and not text.strip():
                empty_documents += 1

            document = {
                "doc_id": doc_id,
                "title": title,
                "text": text,
                "metadata": prepare_metadata(row, location),
            }

            mapping = {
                "internal_id": internal_id,
                "doc_id": doc_id,
            }

            write_jsonl_row(documents_file, document)
            write_jsonl_row(mapping_file, mapping)

    return seen_ids, empty_documents


def convert_queries():
    """Convert raw SciFact queries into the processed JSONL format.

    Returns the set of converted query IDs.

    Raises:
        ValueError: If a record is invalid, has a duplicate ID, or blank query text.
    """
    input_path = RAW_DIR / "queries.jsonl"
    output_path = OUTPUT_DIR / "queries.jsonl"

    seen_ids = set()

    with output_path.open("w", encoding="utf-8") as output_file:
        for line_number, row in read_jsonl(input_path):
            location = f"{input_path}:{line_number}"

            query_id = require_id(row, "_id", location)
            text = require_text(row, "text", location)

            if query_id in seen_ids:
                raise ValueError(
                    f"{location}: duplicate query ID '{query_id}'"
                )

            if not text.strip():
                raise ValueError(
                    f"{location}: query text is empty"
                )

            seen_ids.add(query_id)

            query = {
                "query_id": query_id,
                "text": text,
                "metadata": prepare_metadata(row, location),
            }

            write_jsonl_row(output_file, query)

    return seen_ids


def convert_qrels(document_ids, query_ids):
    """Convert qrels splits and validate referenced queries and documents.

    Args:
        document_ids (set[str]): Valid document IDs from the converted corpus.
        query_ids (set[str]): Valid query IDs from the converted queries.

    Returns per-split counts of judgments, queries, and positive judgments.
    Writes one normalized TSV under ``data/processed/scifact/qrels`` for each
    raw split.

    Raises:
        ValueError: If qrels are missing, malformed, duplicated, or reference unknown IDs.
    """
    input_dir = RAW_DIR / "qrels"
    output_dir = OUTPUT_DIR / "qrels"

    output_dir.mkdir(parents=True, exist_ok=True)

    split_paths = sorted(input_dir.glob("*.tsv"))

    if not split_paths:
        raise ValueError(f"No qrels files found in {input_dir}")

    split_statistics = {}

    for input_path in split_paths:
        split_name = input_path.stem
        output_path = output_dir / input_path.name

        seen_pairs = set()
        split_query_ids = set()
        positive_count = 0

        with (
            input_path.open(
                "r", encoding="utf-8", newline=""
            ) as input_file,
            output_path.open(
                "w", encoding="utf-8", newline=""
            ) as output_file,
        ):
            reader = csv.DictReader(input_file, delimiter="\t")

            expected_fields = {"query-id", "corpus-id", "score"}
            actual_fields = set(reader.fieldnames or [])

            if not expected_fields.issubset(actual_fields):
                raise ValueError(
                    f"{input_path}: unexpected columns "
                    f"{reader.fieldnames}"
                )

            writer = csv.DictWriter(
                output_file,
                fieldnames=["query_id", "doc_id", "relevance"],
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()

            for row in reader:
                location = f"{input_path}:{reader.line_num}"

                query_id = row["query-id"]
                doc_id = row["corpus-id"]

                try:
                    relevance = int(row["score"])
                except (ValueError, TypeError) as exc:
                    raise ValueError(
                        f"{location}: invalid relevance score"
                    ) from exc

                if query_id not in query_ids:
                    raise ValueError(
                        f"{location}: unknown query '{query_id}'"
                    )

                if doc_id not in document_ids:
                    raise ValueError(
                        f"{location}: unknown document '{doc_id}'"
                    )

                pair = (query_id, doc_id)

                if pair in seen_pairs:
                    raise ValueError(
                        f"{location}: duplicate judgment {pair}"
                    )

                seen_pairs.add(pair)
                split_query_ids.add(query_id)

                if relevance > 0:
                    positive_count += 1

                writer.writerow({
                    "query_id": query_id,
                    "doc_id": doc_id,
                    "relevance": relevance,
                })

        split_statistics[split_name] = {
            "judgments": len(seen_pairs),
            "queries": len(split_query_ids),
            "positive_judgments": positive_count,
        }

    return split_statistics

def main():
    """Convert raw SciFact files and write processed data with a manifest.

    Raises:
        FileNotFoundError: If a required raw input path does not exist.
        FileExistsError: If the output directory already exists.
        ValueError: If converted collections are empty or contain invalid records.

    Side effects:
        Creates a new ``data/processed/scifact`` tree containing converted
        documents, queries, ID mappings, qrels, and a manifest. It refuses to
        overwrite an existing output directory, and prints a conversion
        summary when complete.
    """
    required_paths = [
        RAW_DIR / "corpus.jsonl",
        RAW_DIR / "queries.jsonl",
        RAW_DIR / "qrels",
    ]

    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(
                f"Required input not found: {path}"
            )

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Output directory already exists: {OUTPUT_DIR}\n"
            "Inspect it before removing or renaming it."
        )

    OUTPUT_DIR.mkdir(parents=True)

    document_ids, empty_documents = convert_documents()
    query_ids = convert_queries()

    if not document_ids:
        raise ValueError("The document collection is empty.")

    if not query_ids:
        raise ValueError("The query collection is empty.")

    split_statistics = convert_qrels(
        document_ids,
        query_ids,
    )

    manifest = {
        "dataset": "scifact",
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(RAW_DIR.relative_to(PROJECT_ROOT)),
        "documents": len(document_ids),
        "queries": len(query_ids),
        "empty_documents": empty_documents,
        "internal_id_assignment": "zero-based corpus file order",
        "splits": split_statistics,
    }

    manifest_path = OUTPUT_DIR / "manifest.json"

    with manifest_path.open("w", encoding="utf-8") as file:
        json.dump(
            manifest,
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")

    print("SciFact conversion completed.")
    print(f"Documents: {len(document_ids):,}")
    print(f"Queries: {len(query_ids):,}")
    print(f"Empty documents: {empty_documents:,}")

    for split_name, stats in split_statistics.items():
        print(
            f"{split_name}: "
            f"{stats['queries']:,} queries, "
            f"{stats['judgments']:,} judgments"
        )

    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
