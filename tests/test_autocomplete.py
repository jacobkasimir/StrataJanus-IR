import pytest

from stratajanus.retrieval.autocomplete import (
    MarisaAutocomplete,
    SortedAutocomplete,
    Suggestion,
    TrieAutocomplete,
)


VOCABULARY = {
    "protein": 8,
    "proteins": 3,
    "proton": 3,
    "process": 5,
    "café": 2,
    "search": 7,
}


@pytest.fixture(params=["trie", "sorted", "marisa"])
def autocomplete(request):
    if request.param == "marisa":
        pytest.importorskip("marisa_trie")
        return MarisaAutocomplete(VOCABULARY)

    if request.param == "trie":
        return TrieAutocomplete(VOCABULARY)

    return SortedAutocomplete(VOCABULARY)


def test_frequency_and_tie_order(autocomplete):
    assert autocomplete.suggest("pro") == [
        Suggestion("protein", 8),
        Suggestion("process", 5),
        Suggestion("proteins", 3),
        Suggestion("proton", 3),
    ]


def test_top_k(autocomplete):
    assert autocomplete.suggest("pro", top_k=2) == [
        Suggestion("protein", 8),
        Suggestion("process", 5),
    ]


def test_prefix_is_normalized(autocomplete):
    assert autocomplete.suggest("PROT") == [
        Suggestion("protein", 8),
        Suggestion("proteins", 3),
        Suggestion("proton", 3),
    ]

    assert autocomplete.suggest("CAFE\u0301") == [
        Suggestion("café", 2),
    ]


def test_unknown_or_invalid_prefix(autocomplete):
    assert autocomplete.suggest("zzzz") == []
    assert autocomplete.suggest("") == []
    assert autocomplete.suggest("pro!") == []


def test_zero_limit(autocomplete):
    assert autocomplete.suggest("pro", top_k=0) == []


def test_negative_limit_is_rejected(autocomplete):
    with pytest.raises(ValueError, match="top_k"):
        autocomplete.suggest("pro", top_k=-1)


def test_invalid_vocabulary_is_rejected():
    with pytest.raises(ValueError):
        TrieAutocomplete({"word": 0})

    with pytest.raises(ValueError):
        SortedAutocomplete({"": 2})