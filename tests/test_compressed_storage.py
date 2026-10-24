import pytest

from stratajanus.index.compressed_storage import (
    load_index,
    save_index,
)
from stratajanus.index.inverted import build_index
from stratajanus.retrieval.bm25 import BM25


@pytest.fixture
def example_index():
    return build_index([
        {"doc_id": "00123", "title": "Café", "text": "search search"},
        {"doc_id": "empty", "title": "", "text": ""},
        {"doc_id": "last", "title": "", "text": "search engine"},
    ])


def test_compressed_round_trip(tmp_path, example_index):
    directory = tmp_path / "compressed"

    save_index(example_index, directory)
    restored = load_index(directory)

    assert restored == example_index
    assert restored.postings["search"] == [(0, 2), (2, 1)]


@pytest.mark.parametrize("query", ["search", "café", "unknown", ""])
def test_bm25_results_are_preserved(tmp_path, example_index, query):
    directory = tmp_path / "compressed"

    save_index(example_index, directory)
    restored = load_index(directory)

    before = BM25(example_index).search(query)
    after = BM25(restored).search(query)

    assert [item.doc_id for item in after] == [
        item.doc_id for item in before
    ]
    assert [item.score for item in after] == pytest.approx(
        [item.score for item in before]
    )


def test_small_postings_use_two_bytes_per_pair(tmp_path, example_index):
    directory = tmp_path / "compressed"
    save_index(example_index, directory)

    posting_count = sum(
        len(postings) for postings in example_index.postings.values()
    )

    # All gaps and frequencies in this fixture fit in one byte.
    assert (
        directory / "postings.bin"
    ).stat().st_size == 2 * posting_count


def test_empty_index_round_trip(tmp_path):
    directory = tmp_path / "empty"
    original = build_index([])

    save_index(original, directory)

    assert load_index(directory) == original


def test_overwriting_is_rejected(tmp_path, example_index):
    directory = tmp_path / "compressed"
    save_index(example_index, directory)

    with pytest.raises(FileExistsError):
        save_index(example_index, directory)


def test_truncated_postings_are_rejected(tmp_path, example_index):
    directory = tmp_path / "compressed"
    save_index(example_index, directory)

    path = directory / "postings.bin"
    path.write_bytes(path.read_bytes()[:-1])

    with pytest.raises(ValueError, match="Truncated"):
        load_index(directory)