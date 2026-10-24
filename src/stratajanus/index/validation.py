"""Shared structural validation for inverted indexes."""

from stratajanus.index.inverted import InvertedIndex


def validate_index(index: InvertedIndex) -> None:
    """Check the structural consistency of a complete inverted index."""
    if not isinstance(index.postings, dict):
        raise ValueError("Index postings must be a dictionary.")

    if not isinstance(index.doc_lengths, list):
        raise ValueError("Document lengths must be a list.")

    if not isinstance(index.internal_to_external, list):
        raise ValueError("Document IDs must be a list.")

    document_ids = index.internal_to_external
    document_count = len(document_ids)

    if len(index.doc_lengths) != document_count:
        raise ValueError(
            "Document lengths and document IDs have different counts."
        )

    for doc_id in document_ids:
        if not isinstance(doc_id, str) or not doc_id:
            raise ValueError(
                "External document IDs must be nonempty strings."
            )

    if len(set(document_ids)) != document_count:
        raise ValueError("External document IDs must be unique.")

    for length in index.doc_lengths:
        if type(length) is not int or length < 0:
            raise ValueError(
                "Document lengths must be nonnegative integers."
            )

    reconstructed_lengths = [0] * document_count

    for term, postings in index.postings.items():
        if not isinstance(term, str) or not term:
            raise ValueError("Index terms must be nonempty strings.")

        if not isinstance(postings, list) or not postings:
            raise ValueError(
                f"Posting list for {term!r} must be a nonempty list."
            )

        previous_id = -1

        for posting in postings:
            if (
                not isinstance(posting, (tuple, list))
                or len(posting) != 2
            ):
                raise ValueError(
                    f"Invalid posting for term {term!r}."
                )

            internal_id, frequency = posting

            if (
                type(internal_id) is not int
                or not 0 <= internal_id < document_count
            ):
                raise ValueError(
                    f"Invalid document ID in postings for {term!r}."
                )

            if internal_id <= previous_id:
                raise ValueError(
                    f"Postings for {term!r} must have strictly "
                    "increasing document IDs."
                )

            if type(frequency) is not int or frequency <= 0:
                raise ValueError(
                    f"Invalid term frequency for {term!r}."
                )

            reconstructed_lengths[internal_id] += frequency
            previous_id = internal_id

    if reconstructed_lengths != index.doc_lengths:
        raise ValueError(
            "Posting frequencies do not match document lengths."
        )