"""Build and inspect an in-memory inverted index.

Documents receive zero-based internal IDs in input order. Posting lists map
each term to ``(internal_id, term_frequency)`` pairs in ascending internal ID
order; external IDs are kept separately for display and lookup.
"""

from dataclasses import dataclass
from collections import defaultdict, Counter
from stratajanus.text.tokenizer import tokenize


@dataclass
class InvertedIndex:
    """Hold postings and per-document statistics for an in-memory collection.

    Args:
        postings: Mapping from token strings to lists of
            ``(internal_id, term_frequency)`` pairs. Lists produced by
            :func:`build_index` follow ascending internal-ID order.
        doc_lengths: Token count for each internal document ID.
        internal_to_external: External ``doc_id`` for each internal ID.

    Internal IDs are zero-based positions shared by ``doc_lengths`` and
    ``internal_to_external``. External IDs are the caller's original strings.
    The dataclass does not validate manually supplied structures; builders
    return aligned lists and valid posting IDs.
    """

    postings: dict[str, list[tuple[int, int]]]
    doc_lengths: list[int]
    internal_to_external: list[str]

    @property
    def document_count(self) -> int:
        """Number of documents, including documents with no tokens."""
        return len(self.internal_to_external)

    @property
    def average_document_length(self) -> float:
        """Mean token count, or ``0.0`` for an empty collection."""
        if self.document_count == 0:
            return 0.0

        return sum(self.doc_lengths) / self.document_count

    def document_frequency(self, term: str) -> int:
        """Return the number of postings for the exact term; unknown terms yield 0."""
        return len(self.postings.get(term, []))

def build_index(documents: list[dict]) -> InvertedIndex:
    """Tokenize documents and produce an in-memory inverted index.

    Args:
        documents: Ordered iterable of mappings with a nonempty string
            ``doc_id`` and string ``title`` and ``text`` fields. Extra fields
            are ignored.

    Returns:
        An :class:`InvertedIndex` whose internal IDs follow input order,
        lengths count title and body tokens together, and postings contain
        ``(internal_id, term_frequency)`` pairs in that same order.

    Raises:
        TypeError: If an item is not a dictionary.
        ValueError: If required fields are invalid or an external ID repeats.

    Empty input produces an empty index. Input mappings are not modified.
    The title and body are separated by a newline before tokenization.
    """
    postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
    doc_lengths: list[int] = []
    internal_to_external: list[str] = []
    seen_doc_ids: set[str] = set()

    for document in documents:
        if not isinstance(document, dict):
            raise TypeError("Each document must be a dictionary.")

        doc_id = document.get("doc_id")
        title = document.get("title")
        text = document.get("text")

        if not isinstance(doc_id, str) or not doc_id:
            raise ValueError("Document 'doc_id' must be a nonempty string.")

        if not isinstance(title, str):
            raise ValueError(
                f"Document {doc_id!r}: 'title' must be a string."
            )

        if not isinstance(text, str):
            raise ValueError(
                f"Document {doc_id!r}: 'text' must be a string."
            )

        if doc_id in seen_doc_ids:
            raise ValueError(f"Duplicate document ID: {doc_id!r}")

        internal_id = len(internal_to_external)
        seen_doc_ids.add(doc_id)

        # The separator prevents a word at the end of the title from
        # merging with a word at the beginning of the text.
        tokens = tokenize(title + "\n" + text)

        internal_to_external.append(doc_id)
        doc_lengths.append(len(tokens))

        term_frequencies = Counter(tokens)

        for term, frequency in term_frequencies.items():
            postings[term].append((internal_id, frequency))

    return InvertedIndex(
        postings=dict(postings),
        doc_lengths=doc_lengths,
        internal_to_external=internal_to_external,
    )
