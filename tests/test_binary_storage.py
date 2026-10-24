import json

import pytest

from stratajanus.index.binary_storage import (
    MAX_UINT32,
    POSTING,
    UINT32,
    load_index,
    save_index,
)
from stratajanus.index.inverted import (
    InvertedIndex,
    build_index,
)
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


def test_binary_round_trip_preserves_index(
    tmp_path,
    example_index,
):
    directory = tmp_path / "binary-index"

    save_index(example_index, directory)
    restored = load_index(directory)

    assert restored == example_index

    assert restored.internal_to_external[0] == "00123"
    assert restored.postings["café"] == [(0, 1)]
    assert isinstance(restored.postings["search"][0], tuple)


def test_binary_file_sizes_are_predictable(
    tmp_path,
    example_index,
):
    directory = tmp_path / "binary-index"
    save_index(example_index, directory)

    posting_count = sum(
        len(postings)
        for postings in example_index.postings.values()
    )

    assert UINT32.size == 4
    assert POSTING.size == 8

    assert (
        directory / "doc_lengths.bin"
    ).stat().st_size == 4 * example_index.document_count

    assert (
        directory / "postings.bin"
    ).stat().st_size == 8 * posting_count


def test_vocabulary_offset_points_to_correct_postings(
    tmp_path,
    example_index,
):
    directory = tmp_path / "binary-index"
    save_index(example_index, directory)

    vocabulary = json.loads(
        (directory / "vocabulary.json").read_text(
            encoding="utf-8"
        )
    )

    entry = vocabulary["search"]

    with (directory / "postings.bin").open("rb") as file:
        file.seek(entry["offset"])

        block = file.read(
            entry["document_frequency"] * POSTING.size
        )

    decoded = list(POSTING.iter_unpack(block))

    assert decoded == [(0, 3), (1, 1)]


@pytest.mark.parametrize(
    "query",
    ["search", "neural search", "CAFÉ", "unknown", ""],
)
def test_binary_round_trip_preserves_bm25(
    tmp_path,
    example_index,
    query,
):
    directory = tmp_path / "binary-index"

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
    original = build_index([])
    directory = tmp_path / "empty-index"

    save_index(original, directory)

    assert load_index(directory) == original


def test_existing_directory_is_rejected(
    tmp_path,
    example_index,
):
    directory = tmp_path / "binary-index"
    save_index(example_index, directory)

    with pytest.raises(
        FileExistsError,
        match="already exists",
    ):
        save_index(example_index, directory)


def test_truncated_postings_are_rejected(
    tmp_path,
    example_index,
):
    directory = tmp_path / "binary-index"
    save_index(example_index, directory)

    path = directory / "postings.bin"
    path.write_bytes(path.read_bytes()[:-1])

    with pytest.raises(ValueError, match="Truncated postings"):
        load_index(directory)


def test_invalid_document_length_file_size_is_rejected(
    tmp_path,
    example_index,
):
    directory = tmp_path / "binary-index"
    save_index(example_index, directory)

    path = directory / "doc_lengths.bin"
    path.write_bytes(path.read_bytes()[:-1])

    with pytest.raises(
        ValueError,
        match="Invalid document-length file size",
    ):
        load_index(directory)


def test_invalid_offset_is_rejected(
    tmp_path,
    example_index,
):
    directory = tmp_path / "binary-index"
    save_index(example_index, directory)

    path = directory / "vocabulary.json"
    vocabulary = json.loads(path.read_text(encoding="utf-8"))

    first_term = sorted(vocabulary)[0]
    vocabulary[first_term]["offset"] = 1

    path.write_text(
        json.dumps(vocabulary),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid posting offset"):
        load_index(directory)


def test_values_larger_than_uint32_are_rejected(tmp_path):
    # No enormous document is needed: construct a structurally
    # consistent index containing an out-of-range count.
    too_large = MAX_UINT32 + 1

    index = InvertedIndex(
        postings={"word": [(0, too_large)]},
        doc_lengths=[too_large],
        internal_to_external=["large"],
    )

    with pytest.raises(
        ValueError,
        match="unsigned 32-bit integer",
    ):
        save_index(index, tmp_path / "too-large")