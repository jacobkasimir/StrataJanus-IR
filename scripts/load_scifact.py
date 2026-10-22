from pathlib import Path

from beir.datasets.data_loader import GenericDataLoader


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "data" / "raw" / "scifact"


def main():
    split = "train"

    qrels_dir = DATASET_DIR / "qrels"
    available = sorted(path.stem for path in qrels_dir.glob("*.tsv"))
    if not available:
        raise FileNotFoundError(f"No qrels splits found in {qrels_dir}")
    print(f"Available relevance splits: {', '.join(available)}")

    if split not in available:
        raise FileNotFoundError(
            f"Split '{split}' is unavailable. Available splits: {available}"
        )

    corpus = queries = qrels = None
    for current_split in available:
        current_corpus, current_queries, current_qrels = GenericDataLoader(
            data_folder=str(DATASET_DIR)
        ).load(split=current_split)
        assert current_corpus, f"The corpus is empty for {current_split}."
        assert current_queries, f"No queries were loaded for {current_split}."
        assert current_qrels, f"No judgments were loaded for {current_split}."

        for query_id, judgments in current_qrels.items():
            assert query_id in current_queries, (
                f"{current_split} judgments reference missing query: {query_id}"
            )
            for doc_id in judgments:
                assert doc_id in current_corpus, (
                    f"{current_split} judgments reference missing document: {doc_id}"
                )

        print(
            f"{current_split}: {len(current_corpus):,} documents, "
            f"{len(current_queries):,} queries, "
            f"{len(current_qrels):,} queries with judgments"
        )
        if current_split == split:
            corpus, queries, qrels = current_corpus, current_queries, current_qrels

    print("\nDataset consistency checks passed for every available split.\n")

    print(f"Split: {split}")
    print(f"Documents: {len(corpus):,}")
    print(f"Queries loaded: {len(queries):,}")
    print(f"Queries with judgments: {len(qrels):,}")

    query_id = next(iter(qrels))

    print("\nEXAMPLE QUERY")
    print(f"ID: {query_id}")
    print(f"Text: {queries[query_id]}")

    print("\nRELEVANT DOCUMENTS")
    for doc_id, relevance in qrels[query_id].items():
        if relevance <= 0:
            continue

        document = corpus[doc_id]

        print(f"\nDocument ID: {doc_id}")
        print(f"Relevance: {relevance}")
        print(f"Title: {document.get('title', '')}")
        print(f"Text preview: {document.get('text', '')[:500]}")


if __name__ == "__main__":
    main()
