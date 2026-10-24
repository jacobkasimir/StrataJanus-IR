import json

import pytest

from stratajanus.index.inverted import build_index
from stratajanus.index.storage import load_index, save_index
from stratajanus.retrieval.bm25 import BM25


@pytest.fixture
def example_index():
    return build_index([
        {
            "doc_id": "00123",
            "title": "Café Search",
            "text": "search search engine",
        },
        {
            "doc_id": "paper-B",
            "title": "",
            "text": "neural search",
        },
        {
            "doc_id": "empty",
            "title": "",
            "text": "",
        },
    ])


def test_save_creates_required_files(tmp_path, example_index):
    directory = tmp_path / "index"

    save_index(example_index, directory)

    assert (directory / "index.json").is_file()
    assert (directory / "tokenizer_config.json").is_file()
    assert (directory / "manifest.json").is_file()


def test_round_trip_preserves_index(tmp_path, example_index):
    directory = tmp_path / "index"

    save_index(example_index, directory)
    restored = load_index(directory)

    assert restored.postings == example_index.postings
    assert restored.doc_lengths == example_index.doc_lengths
    assert (
        restored.internal_to_external
        == example_index.internal_to_external
    )

    assert isinstance(restored.postings["search"][0], tuple)

    assert restored.internal_to_external[0] == "00123"
    assert "café" in restored.postings


@pytest.mark.parametrize(
    "query",
    ["search", "neural search", "CAFÉ", "unknown", ""],
)
def test_round_trip_preserves_bm25_results(
    tmp_path,
    example_index,
    query,
):
    directory = tmp_path / "index"

    save_index(example_index, directory)
    restored = load_index(directory)

    before = BM25(example_index).search(query)
    after = BM25(restored).search(query)

    assert [result.doc_id for result in after] == [
        result.doc_id for result in before
    ]

    assert [result.score for result in after] == pytest.approx(
        [result.score for result in before]
    )


def test_empty_index_round_trip(tmp_path):
    directory = tmp_path / "empty-index"
    original = build_index([])

    save_index(original, directory)
    restored = load_index(directory)

    assert restored == original
    assert BM25(restored).search("search") == []


def test_existing_directory_is_not_overwritten(
    tmp_path,
    example_index,
):
    directory = tmp_path / "index"

    save_index(example_index, directory)

    before = {
        path.name: path.read_bytes()
        for path in directory.iterdir()
    }

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        save_index(example_index, directory)

    after = {
        path.name: path.read_bytes()
        for path in directory.iterdir()
    }

    assert after == before


def test_missing_file_is_rejected(tmp_path, example_index):
    directory = tmp_path / "index"

    save_index(example_index, directory)
    (directory / "index.json").unlink()

    with pytest.raises(
        FileNotFoundError,
        match="Required index file is missing",
    ):
        load_index(directory)


def test_incompatible_tokenizer_is_rejected(
    tmp_path,
    example_index,
):
    directory = tmp_path / "index"
    save_index(example_index, directory)

    config_path = directory / "tokenizer_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["lowercase"] = False

    config_path.write_text(
        json.dumps(config),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="does not match the index",
    ):
        load_index(directory)


def test_unsupported_format_version_is_rejected(
    tmp_path,
    example_index,
):
    directory = tmp_path / "index"
    save_index(example_index, directory)

    manifest_path = directory / "manifest.json"
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )
    manifest["format_version"] = 999

    manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported index format version",
    ):
        load_index(directory)


def test_inconsistent_document_lengths_are_rejected(
    tmp_path,
    example_index,
):
    directory = tmp_path / "index"
    save_index(example_index, directory)

    index_path = directory / "index.json"
    payload = json.loads(index_path.read_text(encoding="utf-8"))

    payload["doc_lengths"][0] += 1

    index_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Posting frequencies do not match document lengths",
    ):
        load_index(directory)