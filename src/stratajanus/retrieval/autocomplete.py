"""Vocabulary autocomplete implementations for stratajanus."""

import heapq
from bisect import bisect_left
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from stratajanus.text.tokenizer import normalize_prefix


@dataclass(frozen=True)
class Suggestion:
    """An indexed term and its document frequency."""

    term: str
    document_frequency: int


@dataclass
class _TrieNode:
    """One internal trie node."""

    children: dict[str, "_TrieNode"] = field(default_factory=dict)
    term: str | None = None
    document_frequency: int = 0


def _validate_vocabulary(
    vocabulary: Mapping[str, int],
) -> None:
    """Check that vocabulary entries have usable terms and frequencies."""
    for term, frequency in vocabulary.items():
        if not isinstance(term, str) or not term:
            raise ValueError("Vocabulary terms must be nonempty strings.")

        if type(frequency) is not int or frequency <= 0:
            raise ValueError(
                "Document frequencies must be positive integers."
            )


def _prepare_request(prefix: str, top_k: int) -> str | None:
    """Validate the result limit and normalize the typed prefix."""
    if type(top_k) is not int or top_k < 0:
        raise ValueError("top_k must be a nonnegative integer.")

    return normalize_prefix(prefix)


def _best_suggestions(
    candidates: Iterable[tuple[str, int]],
    top_k: int,
) -> list[Suggestion]:
    """Select suggestions by frequency, then alphabetical term order."""
    best = heapq.nsmallest(
        top_k,
        (
            (-frequency, term)
            for term, frequency in candidates
        ),
    )

    return [
        Suggestion(
            term=term,
            document_frequency=-negative_frequency,
        )
        for negative_frequency, term in best
    ]


class TrieAutocomplete:
    """Suggest indexed vocabulary terms using a Python trie."""

    def __init__(self, vocabulary: Mapping[str, int]):
        _validate_vocabulary(vocabulary)
        self.root = _TrieNode()

        for term, frequency in vocabulary.items():
            node = self.root

            for character in term:
                node = node.children.setdefault(
                    character,
                    _TrieNode(),
                )

            node.term = term
            node.document_frequency = frequency

    def suggest(
        self,
        prefix: str,
        top_k: int = 10,
    ) -> list[Suggestion]:
        """Return the best indexed terms beginning with prefix."""
        normalized = _prepare_request(prefix, top_k)

        if normalized is None or top_k == 0:
            return []

        node = self.root

        for character in normalized:
            node = node.children.get(character)

            if node is None:
                return []

        def candidates():
            stack = [node]

            while stack:
                current = stack.pop()

                if current.term is not None:
                    yield (
                        current.term,
                        current.document_frequency,
                    )

                stack.extend(current.children.values())

        return _best_suggestions(candidates(), top_k)


class SortedAutocomplete:
    """Suggest terms using a sorted list and binary search."""

    def __init__(self, vocabulary: Mapping[str, int]):
        _validate_vocabulary(vocabulary)

        self.terms = sorted(vocabulary)
        self.frequencies = [
            vocabulary[term]
            for term in self.terms
        ]

    def suggest(
        self,
        prefix: str,
        top_k: int = 10,
    ) -> list[Suggestion]:
        """Find the prefix range, then rank matching terms."""
        normalized = _prepare_request(prefix, top_k)

        if normalized is None or top_k == 0:
            return []

        start = bisect_left(self.terms, normalized)

        def candidates():
            position = start

            while (
                position < len(self.terms)
                and self.terms[position].startswith(normalized)
            ):
                yield (
                    self.terms[position],
                    self.frequencies[position],
                )
                position += 1

        return _best_suggestions(candidates(), top_k)


class MarisaAutocomplete:
    """Suggest terms using marisa-trie plus external frequency data.

    Requires the optional third-party package ``marisa-trie``.
    """

    def __init__(self, vocabulary: Mapping[str, int]):
        _validate_vocabulary(vocabulary)

        try:
            import marisa_trie
        except ImportError as exc:
            raise RuntimeError(
                "Install marisa-trie to use MarisaAutocomplete."
            ) from exc

        self.frequencies = dict(vocabulary)
        self.trie = marisa_trie.Trie(vocabulary)

    def suggest(
        self,
        prefix: str,
        top_k: int = 10,
    ) -> list[Suggestion]:
        """Get matching trie keys and rank them by frequency."""
        normalized = _prepare_request(prefix, top_k)

        if normalized is None or top_k == 0:
            return []

        return _best_suggestions(
            (
                (term, self.frequencies[term])
                for term in self.trie.keys(normalized)
            ),
            top_k,
        )