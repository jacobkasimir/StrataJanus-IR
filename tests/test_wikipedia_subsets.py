import hashlib
import json

import pytest

from scripts.prepare_wikipedia_subsets import write_subsets


def test_subsets_are_nested_and_fingerprinted(tmp_path):
    rows = [
        {"id": "1", "title": "First", "text": "First body", "url": ""},
        {"id": "2", "title": "Empty", "text": "   ", "url": ""},
        {"id": "3", "title": "Second", "text": "Second body", "url": ""},
        {"id": "4", "title": "Third", "text": "Third body", "url": ""},
    ]

    output = tmp_path / "subsets"

    manifest = write_subsets(
        rows,
        [1, 3],
        output,
        source={"dataset": "synthetic-test"},
    )

    small = (output / "1" / "documents.jsonl").read_bytes()
    large = (output / "3" / "documents.jsonl").read_bytes()

    assert large.startswith(small)
    assert len(small.splitlines()) == 1
    assert len(large.splitlines()) == 3

    documents = [
        json.loads(line)
        for line in large.splitlines()
    ]

    assert [doc["doc_id"] for doc in documents] == [
        "wikipedia-en:1",
        "wikipedia-en:3",
        "wikipedia-en:4",
    ]

    assert manifest["empty_bodies_skipped"] == 1
    assert manifest["subsets"]["3"]["sha256"] == (
        hashlib.sha256(large).hexdigest()
    )


def test_existing_output_is_rejected(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()

    with pytest.raises(FileExistsError):
        write_subsets([], [1], output, source={})


def test_insufficient_source_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="Source ended"):
        write_subsets(
            [],
            [10],
            tmp_path / "incomplete",
            source={},
        )