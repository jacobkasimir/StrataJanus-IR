import math
from collections import Counter

import pytest

from stratajanus.index.inverted import build_index
from stratajanus.retrieval.bm25 import BM25
from stratajanus.text.tokenizer import tokenize

@pytest.fixture
def toy_documents():
    return [
        {
            "doc_id": "toy-0",
            "title": "",
            "text": "neural search improves retrieval",
        },
        {
            "doc_id": "toy-1",
            "title": "",
            "text": "sparse retrieval uses inverted indexes",
        },
        {
            "doc_id": "toy-2",
            "title": "",
            "text": (
                "hybrid search combines sparse "
                "and neural retrieval"
            ),
        },
    ]


def test_search_returns_matching_documents_in_rank_order(
    toy_documents,
):
    ranker = BM25(build_index(toy_documents))

    results = ranker.search("neural search")

    # Both terms occur once in toy-0 and toy-2.
    # toy-0 is shorter, so it receives the higher score.
    assert [result.doc_id for result in results] == [
        "toy-0",
        "toy-2",
    ]

    assert results[0].score > results[1].score > 0


def test_single_term_score_matches_hand_calculation(
    toy_documents,
):
    ranker = BM25(build_index(toy_documents))

    results = ranker.search("search")

    # N = 3, df("search") = 2
    idf = math.log(1 + (3 - 2 + 0.5) / (2 + 0.5))

    # toy-0: tf = 1, document length = 4, average length = 16/3
    expected = idf * (
        1 * (1.2 + 1)
        / (
            1
            + 1.2 * (
                1 - 0.75
                + 0.75 * 4 / (16 / 3)
            )
        )
    )

    assert results[0].doc_id == "toy-0"
    assert results[0].score == pytest.approx(expected)


def test_unknown_query_returns_no_results(toy_documents):
    ranker = BM25(build_index(toy_documents))

    assert ranker.search("zzzznotincorpus") == []


def test_empty_query_returns_no_results(toy_documents):
    ranker = BM25(build_index(toy_documents))

    assert ranker.search("") == []
    assert ranker.search("!!!") == []


def test_repeated_query_terms_count_once(toy_documents):
    ranker = BM25(build_index(toy_documents))

    assert ranker.search("search search") == ranker.search("search")


def test_top_k_limits_results(toy_documents):
    ranker = BM25(build_index(toy_documents))

    results = ranker.search("retrieval", top_k=1)

    assert len(results) == 1
    assert results[0].doc_id == "toy-0"


def test_nonpositive_top_k_returns_no_results(toy_documents):
    ranker = BM25(build_index(toy_documents))

    assert ranker.search("search", top_k=0) == []
    assert ranker.search("search", top_k=-1) == []


def test_ties_use_internal_document_id():
    index = build_index([
        {"doc_id": "z", "title": "", "text": "search"},
        {"doc_id": "a", "title": "", "text": "search"},
    ])

    results = BM25(index).search("search")

    # Input order, not alphabetical external-ID order.
    assert [result.doc_id for result in results] == ["z", "a"]
    assert results[0].score == results[1].score


def test_empty_collection_returns_no_results():
    assert BM25(build_index([])).search("search") == []


def test_collection_of_empty_documents_returns_no_results():
    index = build_index([
        {"doc_id": "empty", "title": "", "text": ""},
    ])

    assert BM25(index).search("search") == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"k1": 0},
        {"k1": -1},
        {"k1": float("nan")},
        {"b": -0.1},
        {"b": 1.1},
    ],
)
def test_invalid_parameters_are_rejected(kwargs):
    index = build_index([])

    with pytest.raises(ValueError):
        BM25(index, **kwargs)

def reference_bm25(documents, query, k1=1.2, b=0.75):
    """
    Slow correctness reference.

    Deliberately does not use InvertedIndex or posting lists.
    """
    tokenized = [
        tokenize(document["title"] + "\n" + document["text"])
        for document in documents
    ]

    if not tokenized:
        return []

    lengths = [len(tokens) for tokens in tokenized]
    average_length = sum(lengths) / len(lengths)

    if average_length == 0:
        return []

    term_counts = [Counter(tokens) for tokens in tokenized]
    query_terms = sorted(set(tokenize(query)))

    results = []

    for internal_id, counts in enumerate(term_counts):
        score = 0.0

        for term in query_terms:
            frequency = counts.get(term, 0)

            if frequency == 0:
                continue

            document_frequency = sum(
                1
                for other_counts in term_counts
                if term in other_counts
            )

            idf = math.log(
                1
                + (
                    len(documents) - document_frequency + 0.5
                )
                / (document_frequency + 0.5)
            )

            score += idf * (
                frequency * (k1 + 1)
                / (
                    frequency
                    + k1 * (
                        1 - b
                        + b * lengths[internal_id] / average_length
                    )
                )
            )

        if score > 0:
            results.append((internal_id, score))

    return sorted(
        results,
        key=lambda result: (-result[1], result[0]),
    )


@pytest.mark.parametrize(
    "query",
    [
        "neural search",
        "retrieval",
        "sparse unknown",
        "search search",
        "unknown",
        "",
    ],
)
def test_bm25_matches_brute_force_reference(
    toy_documents,
    query,
):
    documents = toy_documents + [
        {
            "doc_id": "repeat",
            "title": "Search",
            "text": "search search retrieval",
        },
        {
            "doc_id": "empty",
            "title": "",
            "text": "",
        },
    ]

    actual = BM25(build_index(documents)).search(
        query,
        top_k=len(documents),
    )

    expected = reference_bm25(documents, query)

    assert [result.internal_id for result in actual] == [
        internal_id
        for internal_id, _ in expected
    ]

    assert [result.score for result in actual] == pytest.approx(
        [score for _, score in expected]
    )