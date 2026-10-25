"""Read canonical SciFact queries and relevance judgments."""

import csv
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    """Return a SHA-256 fingerprint of a file's contents."""
    digest = hashlib.sha256()

    with Path(path).open("rb") as file:
        for block in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def load_queries(path: Path) -> dict[str, str]:
    """Read canonical query IDs and their original text from JSONL."""
    queries = {}

    with Path(path).open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path}, line {line_number}."
                ) from exc

            if not isinstance(row, dict):
                raise ValueError(
                    f"Query at line {line_number} is not an object."
                )

            query_id = row.get("query_id")
            text = row.get("text")

            if (
                not isinstance(query_id, str)
                or not query_id
                or not isinstance(text, str)
                or not text.strip()
            ):
                raise ValueError(
                    f"Invalid query at line {line_number}."
                )

            if query_id in queries:
                raise ValueError(
                    f"Duplicate query ID: {query_id!r}"
                )

            queries[query_id] = text

    return queries


def load_qrels(
    path: Path,
) -> dict[str, dict[str, int]]:
    """Read canonical query/document relevance judgments from TSV."""
    qrels: dict[str, dict[str, int]] = {}

    with Path(path).open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file, delimiter="\t")

        expected = {
            "query_id",
            "doc_id",
            "relevance",
        }

        if not expected.issubset(reader.fieldnames or []):
            raise ValueError(
                f"Unexpected qrels columns: {reader.fieldnames}"
            )

        for row in reader:
            query_id = row["query_id"]
            doc_id = row["doc_id"]

            if not query_id or not doc_id:
                raise ValueError(
                    f"Missing ID in {path}, line {reader.line_num}."
                )

            try:
                relevance = int(row["relevance"])
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Invalid relevance in {path}, "
                    f"line {reader.line_num}."
                ) from exc

            if relevance < 0:
                raise ValueError(
                    f"Negative relevance in {path}, "
                    f"line {reader.line_num}."
                )

            judgments = qrels.setdefault(query_id, {})

            if doc_id in judgments:
                raise ValueError(
                    f"Duplicate judgment for "
                    f"{query_id!r}, {doc_id!r}."
                )

            judgments[doc_id] = relevance

    return qrels