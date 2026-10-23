import csv
import json

import pytest

from scripts import prepare_scifact as converter


def write_jsonl(path, rows):
    """Write test records to a JSON Lines file.

    Args:
        path (Path): Destination file path.
        rows (Iterable[dict[str, Any]]): Records to serialize.

    Returns:
        None: Creates parent directories and writes the records.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(
                json.dumps(row, ensure_ascii=False) + "\n"
            )


def read_jsonl(path):
    """Load nonblank records from a JSON Lines file.

    Args:
        path (Path): Source file path.

    Returns:
        list[dict[str, Any]]: Decoded JSON objects in file order.
    """
    with path.open("r", encoding="utf-8") as file:
        return [
            json.loads(line)
            for line in file
            if line.strip()
        ]


def write_qrels(path, rows):
    """Write relevance judgments using the original BEIR TSV columns.

    Args:
        path (Path): Destination TSV path.
        rows (Iterable[tuple[str, str, int]]): Query ID, document ID, and score rows.

    Returns:
        None: Creates parent directories and writes the TSV data.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(
            file,
            delimiter="\t",
            lineterminator="\n",
        )

        writer.writerow(["query-id", "corpus-id", "score"])
        writer.writerows(rows)

@pytest.fixture
def dataset(tmp_path, monkeypatch):
    """Create a miniature SciFact dataset isolated in a temporary directory.

    Args:
        tmp_path (Path): Pytest temporary directory.
        monkeypatch (pytest.MonkeyPatch): Fixture for redirecting converter paths.

    Returns:
        dict[str, Path]: Raw and processed dataset directory paths.
    """
    project_root = tmp_path / "strata"

    raw_dir = project_root / "data" / "raw" / "scifact"
    output_dir = project_root / "data" / "processed" / "scifact"

    write_jsonl(
        raw_dir / "corpus.jsonl",
        [
            {
                "_id": "d1",
                "title": "First document",
                "text": "First abstract.",
            },
            {
                "_id": "d2",
                "title": "Second document",
                "text": "Second abstract.",
            },
        ],
    )

    write_jsonl(
        raw_dir / "queries.jsonl",
        [
            {
                "_id": "q1",
                "text": "A scientific claim.",
            }
        ],
    )

    write_qrels(
        raw_dir / "qrels" / "train.tsv",
        [
            ("q1", "d1", 1),
        ],
    )

    monkeypatch.setattr(
        converter,
        "PROJECT_ROOT",
        project_root,
    )

    monkeypatch.setattr(
        converter,
        "RAW_DIR",
        raw_dir,
    )

    monkeypatch.setattr(
        converter,
        "OUTPUT_DIR",
        output_dir,
    )

    return {
        "raw": raw_dir,
        "output": output_dir,
    }

#---TEST1---
def test_two_valid_documents_get_contiguous_ids(dataset):
    """Verify document conversion preserves order and assigns contiguous IDs.

    Args:
        dataset (dict[str, Path]): Miniature dataset fixture.

    Returns:
        None: Assertions validate converted documents, mappings, and manifest.
    """
    converter.main()

    documents = read_jsonl(
        dataset["output"] / "documents.jsonl"
    )

    mapping = read_jsonl(
        dataset["output"] / "doc_ids.jsonl"
    )

    assert len(documents) == 2

    assert [doc["doc_id"] for doc in documents] == [
        "d1",
        "d2",
    ]

    assert mapping == [
        {"internal_id": 0, "doc_id": "d1"},
        {"internal_id": 1, "doc_id": "d2"},
    ]

    assert (
        dataset["output"] / "manifest.json"
    ).is_file()


#---TEST2---
def test_duplicate_document_id_is_rejected(dataset):
    """Verify duplicate corpus identifiers cause conversion to fail.

    Args:
        dataset (dict[str, Path]): Miniature dataset fixture.

    Returns:
        None: Asserts that conversion raises ``ValueError``.
    """
    write_jsonl(
        dataset["raw"] / "corpus.jsonl",
        [
            {
                "_id": "d1",
                "title": "First title",
                "text": "First abstract.",
            },
            {
                "_id": "d1",
                "title": "Another title",
                "text": "Another abstract.",
            },
        ],
    )

    with pytest.raises(
        ValueError,
        match="duplicate document ID",
    ):
        converter.main()

#---TEST3---
def test_missing_document_text_is_rejected(dataset):
    """Verify corpus records without text are rejected.

    Args:
        dataset (dict[str, Path]): Miniature dataset fixture.

    Returns:
        None: Asserts that conversion raises ``ValueError``.
    """
    write_jsonl(
        dataset["raw"] / "corpus.jsonl",
        [
            {
                "_id": "d1",
                "title": "A document without text",
            }
        ],
    )

    with pytest.raises(
        ValueError,
        match="'text' must be a string",
    ):
        converter.main()

#---TEST4---
def test_missing_title_defaults_to_empty_string(dataset):
    """Verify an omitted document title is converted to an empty string.

    Args:
        dataset (dict[str, Path]): Miniature dataset fixture.

    Returns:
        None: Assertions validate the converted title and text.
    """
    write_jsonl(
        dataset["raw"] / "corpus.jsonl",
        [
            {
                "_id": "d1",
                "text": "An abstract without a title.",
            }
        ],
    )

    converter.main()

    documents = read_jsonl(
        dataset["output"] / "documents.jsonl"
    )

    assert len(documents) == 1
    assert documents[0]["title"] == ""
    assert documents[0]["text"] == (
        "An abstract without a title."
    )

#---TEST5---
@pytest.mark.parametrize(
    "query_text",
    ["", "   ", "\n\t"],
)
def test_empty_query_text_is_rejected(dataset, query_text):
    """Verify blank query text is rejected.

    Args:
        dataset (dict[str, Path]): Miniature dataset fixture.
        query_text (str): Blank or whitespace-only query text.

    Returns:
        None: Asserts that conversion raises ``ValueError``.
    """
    write_jsonl(
        dataset["raw"] / "queries.jsonl",
        [
            {
                "_id": "q1",
                "text": query_text,
            }
        ],
    )

    with pytest.raises(
        ValueError,
        match="query text is empty",
    ):
        converter.main()


#---TEST6---
def test_qrel_with_unknown_document_is_rejected(dataset):
    """Verify qrels referencing an unknown document are rejected.

    Args:
        dataset (dict[str, Path]): Miniature dataset fixture.

    Returns:
        None: Asserts that conversion raises ``ValueError``.
    """
    write_qrels(
        dataset["raw"] / "qrels" / "train.tsv",
        [
            ("q1", "missing-document", 1),
        ],
    )

    with pytest.raises(
        ValueError,
        match="unknown document",
    ):
        converter.main()

#---TEST7---
def test_qrel_with_unknown_query_is_rejected(dataset):
    """Verify qrels referencing an unknown query are rejected.

    Args:
        dataset (dict[str, Path]): Miniature dataset fixture.

    Returns:
        None: Asserts that conversion raises ``ValueError``.
    """
    write_qrels(
        dataset["raw"] / "qrels" / "train.tsv",
        [
            ("missing-query", "d1", 1),
        ],
    )

    with pytest.raises(
        ValueError,
        match="unknown query",
    ):
        converter.main()

#---TEST8---
def test_unicode_text_is_preserved(dataset):
    """Verify Unicode document and query text survives conversion unchanged.

    Args:
        dataset (dict[str, Path]): Miniature dataset fixture.

    Returns:
        None: Assertions validate decoded content and UTF-8 output.
    """
    title = "Überprüfung der Wirkung"
    text = "Café, β-cells, inflammation — 日本語."
    query_text = "Verändert β die Wirkung?"

    write_jsonl(
        dataset["raw"] / "corpus.jsonl",
        [
            {
                "_id": "d1",
                "title": title,
                "text": text,
            }
        ],
    )

    write_jsonl(
        dataset["raw"] / "queries.jsonl",
        [
            {
                "_id": "q1",
                "text": query_text,
            }
        ],
    )

    converter.main()

    documents = read_jsonl(
        dataset["output"] / "documents.jsonl"
    )

    queries = read_jsonl(
        dataset["output"] / "queries.jsonl"
    )

    assert documents[0]["title"] == title
    assert documents[0]["text"] == text
    assert queries[0]["text"] == query_text

    raw_output = (
        dataset["output"] / "documents.jsonl"
    ).read_text(encoding="utf-8")

    assert "日本語" in raw_output

#---TEST9---
def test_document_id_leading_zeros_are_preserved(dataset):
    """Verify identifiers with leading zeroes remain strings in all outputs.

    Args:
        dataset (dict[str, Path]): Miniature dataset fixture.

    Returns:
        None: Assertions validate corpus, mapping, and qrels identifiers.
    """
    write_jsonl(
        dataset["raw"] / "corpus.jsonl",
        [
            {
                "_id": "00123",
                "title": "Leading-zero ID",
                "text": "Example abstract.",
            }
        ],
    )

    write_qrels(
        dataset["raw"] / "qrels" / "train.tsv",
        [
            ("q1", "00123", 1),
        ],
    )

    converter.main()

    documents = read_jsonl(
        dataset["output"] / "documents.jsonl"
    )

    mapping = read_jsonl(
        dataset["output"] / "doc_ids.jsonl"
    )

    assert documents[0]["doc_id"] == "00123"

    assert mapping == [
        {"internal_id": 0, "doc_id": "00123"},
    ]

    qrels_path = (
        dataset["output"] / "qrels" / "train.tsv"
    )

    with qrels_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        judgments = list(
            csv.DictReader(file, delimiter="\t")
        )

    assert judgments == [
        {
            "query_id": "q1",
            "doc_id": "00123",
            "relevance": "1",
        }
    ]

#---TEST10---
def test_existing_output_directory_is_not_overwritten(dataset):
    """Verify a second conversion preserves an existing output directory.

    Args:
        dataset (dict[str, Path]): Miniature dataset fixture.

    Returns:
        None: Asserts that conversion fails without changing existing files.
    """
    converter.main()

    output_dir = dataset["output"]

    before = {
        path.relative_to(output_dir): path.read_bytes()
        for path in output_dir.rglob("*")
        if path.is_file()
    }

    with pytest.raises(
        FileExistsError,
        match="Output directory already exists",
    ):
        converter.main()

    after = {
        path.relative_to(output_dir): path.read_bytes()
        for path in output_dir.rglob("*")
        if path.is_file()
    }

    assert after == before
