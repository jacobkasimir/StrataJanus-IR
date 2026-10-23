from stratajanus.index.inverted import build_index
from stratajanus.index.inverted import InvertedIndex
import pytest


def test_inverted_index_data_structure():
    index = InvertedIndex(
        postings={
            "search": [(0, 1), (2, 1)],
            "retrieval": [(0, 1), (1, 1), (2, 1)],
        },
        doc_lengths=[4, 5, 7],
        internal_to_external=["toy-0", "toy-1", "toy-2"],
    )

    assert index.document_count == 3
    assert index.average_document_length == 16 / 3

    assert index.document_frequency("search") == 2
    assert index.document_frequency("retrieval") == 3
    assert index.document_frequency("unknown") == 0

    assert index.internal_to_external[2] == "toy-2"
    assert index.doc_lengths[2] == 7


def test_empty_inverted_index():
    index = InvertedIndex(
        postings={},
        doc_lengths=[],
        internal_to_external=[],
    )

    assert index.document_count == 0
    assert index.average_document_length == 0.0
    assert index.document_frequency("search") == 0


def test_toy_corpus():
    documents = [
        {
            "doc_id": "toy-0",
            "title": "",
            "text": "neural search improves retrieval",
            "metadata": {},
        },
        {
            "doc_id": "toy-1",
            "title": "",
            "text": "sparse retrieval uses inverted indexes",
            "metadata": {},
        },
        {
            "doc_id": "toy-2",
            "title": "",
            "text": "hybrid search combines sparse and neural retrieval",
            "metadata": {},
        },
    ]

    index = build_index(documents)

    assert index.internal_to_external == [
        "toy-0",
        "toy-1",
        "toy-2",
    ]
    assert index.doc_lengths == [4, 5, 7]
    assert index.postings["search"] == [(0, 1), (2, 1)]
    assert index.postings["retrieval"] == [
        (0, 1),
        (1, 1),
        (2, 1),
    ]


def test_repeated_terms_have_correct_frequency():
    index = build_index([
        {
            "doc_id": "repeat",
            "title": "",
            "text": "search search engine",
        }
    ])

    assert index.doc_lengths == [3]
    assert index.postings["search"] == [(0, 2)]
    assert index.postings["engine"] == [(0, 1)]


def test_empty_document_keeps_its_id():
    index = build_index([
        {
            "doc_id": "empty",
            "title": "",
            "text": "",
        }
    ])

    assert index.document_count == 1
    assert index.internal_to_external == ["empty"]
    assert index.doc_lengths == [0]
    assert index.postings == {}


def test_title_and_text_are_both_indexed():
    index = build_index([
        {
            "doc_id": "titled",
            "title": "Neural Search",
            "text": "Search works",
        }
    ])

    assert index.doc_lengths == [4]
    assert index.postings["neural"] == [(0, 1)]
    assert index.postings["search"] == [(0, 2)]


def test_duplicate_document_ids_are_rejected():
    documents = [
        {"doc_id": "same", "title": "", "text": "first"},
        {"doc_id": "same", "title": "", "text": "second"},
    ]

    with pytest.raises(ValueError, match="Duplicate document ID"):
        build_index(documents)


def test_empty_collection_produces_empty_index():
    index = build_index([])

    assert index.document_count == 0
    assert index.average_document_length == 0.0
    assert index.postings == {}
    assert index.doc_lengths == []

def test_postings_follow_internal_document_id_order():
    documents = [
        {"doc_id": "z", "title": "", "text": "shared"},
        {"doc_id": "a", "title": "", "text": "other"},
        {"doc_id": "m", "title": "", "text": "shared shared"},
    ]

    index = build_index(documents)

    # IDs follow input order, not alphabetical order of external IDs.
    assert index.internal_to_external == ["z", "a", "m"]
    assert index.postings["shared"] == [(0, 1), (2, 2)]
    assert index.doc_lengths == [1, 1, 2]

def test_build_index_does_not_modify_input_documents():
    documents = [
        {
            "doc_id": "original",
            "title": "Original Title",
            "text": "Original Text",
            "metadata": {"source": "toy"},
        }
    ]

    index = build_index(documents)

    assert documents == [
        {
            "doc_id": "original",
            "title": "Original Title",
            "text": "Original Text",
            "metadata": {"source": "toy"},
        }
    ]
    assert index.postings["original"] == [(0, 2)]

def test_document_frequency_differs_from_term_frequency():
    index = build_index([
        {"doc_id": "d0", "title": "", "text": "search search search"},
        {"doc_id": "d1", "title": "", "text": "search"},
    ])

    assert index.postings["search"] == [(0, 3), (1, 1)]

    # Two documents contain "search"...
    assert index.document_frequency("search") == 2

    # ...but it occurs four times in total.
    assert sum(
        frequency
        for _, frequency in index.postings["search"]
    ) == 4

def test_unicode_forms_and_case_share_a_posting():
    index = build_index([
        {
            "doc_id": "unicode",
            "title": "CAFÉ",
            "text": "cafe\u0301",
        }
    ])

    # "CAFÉ" and "cafe" + combining accent should both become "café".
    assert index.doc_lengths == [2]
    assert index.postings["café"] == [(0, 2)]

def test_title_and_text_do_not_merge_at_boundary():
    index = build_index([
        {
            "doc_id": "boundary",
            "title": "neural",
            "text": "search",
        }
    ])

    assert index.doc_lengths == [2]
    assert index.postings["neural"] == [(0, 1)]
    assert index.postings["search"] == [(0, 1)]
    assert "neuralsearch" not in index.postings


def test_empty_document_between_nonempty_documents_keeps_id_positions():
    documents = [
        {"doc_id": "first", "title": "", "text": "alpha"},
        {"doc_id": "empty", "title": "", "text": ""},
        {"doc_id": "last", "title": "", "text": "alpha"},
    ]

    index = build_index(documents)

    assert index.internal_to_external == [
        "first",
        "empty",
        "last",
    ]
    assert index.doc_lengths == [1, 0, 1]
    assert index.postings["alpha"] == [(0, 1), (2, 1)]


