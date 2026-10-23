from dataclasses import dataclass
from collections import defaultdict, Counter
from stratajanus.text.tokenizer import tokenize


@dataclass
class InvertedIndex:
    """
    An in-memory inverted index.

    Posting lists use internal document IDs, which are positions in
    doc_lengths and internal_to_external.
    """

    postings: dict[str, list[tuple[int, int]]]
    doc_lengths: list[int]
    internal_to_external: list[str]

    @property
    def document_count(self) -> int:
        return len(self.internal_to_external)

    @property
    def average_document_length(self) -> float:
        if self.document_count == 0:
            return 0.0

        return sum(self.doc_lengths) / self.document_count

    def document_frequency(self, term: str) -> int:
        return len(self.postings.get(term, []))

def build_index(documents: list[dict]) -> InvertedIndex:
    """
    Build an in-memory inverted index from canonical documents.

    Documents are assigned internal IDs 0, 1, 2, ... in input order.
    Each document must have string fields: doc_id, title, and text.
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