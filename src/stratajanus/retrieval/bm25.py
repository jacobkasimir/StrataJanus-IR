"""Okapi BM25 ranking over :class:`~stratajanus.index.inverted.InvertedIndex`."""

import heapq
import math
from collections import defaultdict
from dataclasses import dataclass

from stratajanus.index.inverted import InvertedIndex
from stratajanus.text.tokenizer import tokenize


@dataclass(frozen=True)
class SearchResult:
    """One ranked document, with its internal and external identifiers.

    Attributes:
        internal_id: Zero-based position used by the index and input document
            sequence.
        doc_id: Original external document identifier.
        score: Nonnegative BM25 contribution sum for matched query terms. This
            is a ranking score, not a probability.
    """
    internal_id: int
    doc_id: str
    score: float


class BM25:
    """Score matching documents with the Okapi BM25 formula.

    Args:
        index: In-memory index whose postings and document statistics are
            treated as read-only for this ranker's lifetime.
        k1: Positive finite term-frequency saturation parameter (default 1.2).
        b: Finite document-length normalization parameter in ``[0, 1]``
            (default 0.75).

    The implementation uses ``log(1 + (N - df + 0.5) / (df + 0.5))`` for
    IDF and sums the standard BM25 term contribution. Repeated normalized
    query terms count once. Results sort by descending score, with ties broken
    by ascending internal ID, preserving input order independently of external
    ID spelling. Zero-score documents are omitted.
    """

    def __init__(
        self,
        index: InvertedIndex,
        k1: float = 1.2,
        b: float = 0.75,
    ):
        """Create a ranker; invalid ``k1`` or ``b`` raises ``ValueError``."""
        if not math.isfinite(k1) or k1 <= 0:
            raise ValueError("k1 must be finite and greater than zero.")

        if not math.isfinite(b) or not 0 <= b <= 1:
            raise ValueError("b must be finite and between 0 and 1.")

        self.index = index
        self.k1 = k1
        self.b = b

        # Compute these once, rather than repeatedly during scoring.
        self.document_count = index.document_count
        self.average_document_length = index.average_document_length

    def search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Return up to ``top_k`` positive-scoring matches for ``query``.

        Args:
            query: Text normalized with the index tokenizer.
            top_k: Maximum result count; nonpositive values return no results.

        Returns:
            Results containing internal ID, original external ``doc_id``, and
            BM25 score, in descending score order with deterministic ID ties.
            Empty/unknown queries and empty or all-zero-length collections
            return an empty list. Query terms are deduplicated after
            tokenization.

        Raises:
            TypeError: If ``query`` is not a string.
        """
        if top_k <= 0:
            return []

        # Sorting gives a deterministic accumulation order.
        query_terms = sorted(set(tokenize(query)))

        if not query_terms:
            return []

        if (
            self.document_count == 0
            or self.average_document_length == 0
        ):
            return []

        scores: dict[int, float] = defaultdict(float)

        for term in query_terms:
            postings = self.index.postings.get(term, [])

            if not postings:
                continue

            document_frequency = len(postings)

            idf = math.log1p(
                (
                    self.document_count
                    - document_frequency
                    + 0.5
                )
                / (document_frequency + 0.5)
            )

            for internal_id, term_frequency in postings:
                document_length = self.index.doc_lengths[internal_id]

                length_normalization = (
                    1
                    - self.b
                    + self.b
                    * document_length
                    / self.average_document_length
                )

                numerator = term_frequency * (self.k1 + 1)

                denominator = (
                    term_frequency
                    + self.k1 * length_normalization
                )

                scores[internal_id] += (
                    idf * numerator / denominator
                )

        # Smallest (-score, ID) means highest score, then lowest ID.
        best = heapq.nsmallest(
            top_k,
            scores.items(),
            key=lambda item: (-item[1], item[0]),
        )

        return [
            SearchResult(
                internal_id=internal_id,
                doc_id=self.index.internal_to_external[internal_id],
                score=score,
            )
            for internal_id, score in best
        ]
