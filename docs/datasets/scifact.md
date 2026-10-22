# SciFact dataset provenance

## Source

- Dataset: SciFact, distributed in BEIR's `scifact` format.
- Download URL: <https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip>
- Retrieval method: `beir.util.download_and_unzip`, called by `scripts/download_scifact.py`.
- Local extraction directory: `data/raw/scifact/` (ignored by Git).
- BEIR dataset documentation: <https://github.com/beir-cellar/beir/wiki/Datasets-available>
- This repository keeps the downloaded source files unchanged. No acquisition date is asserted because it was not recorded when these files were downloaded.

## Files

- `corpus.jsonl`: document IDs, titles, and text.
- `queries.jsonl`: query IDs and text.
- `qrels/train.tsv` and `qrels/test.tsv`: judged query-document relevance labels.

The dataset as extracted here has 5,183 documents, 809 training queries with judgments, and 300 test queries with judgments. `scripts/load_scifact.py` checks that every judged query and document ID resolves in the loaded source data and prints a training query with its positively judged documents.

## SHA-256 checksums

These hashes identify the four local source files present when this record was created. They can be recomputed with `shasum -a 256 data/raw/scifact/corpus.jsonl data/raw/scifact/queries.jsonl data/raw/scifact/qrels/train.tsv data/raw/scifact/qrels/test.tsv`.

| File | SHA-256 |
| --- | --- |
| `corpus.jsonl` | `dec31c8182f3d744c7d2c09423756fd1d17cbef75808db13ba01cc0aab4d1ac6` |
| `queries.jsonl` | `8ff84a7c903f722981cd8d595c022660140c51867b27608a6d4910b86080313` |
| `qrels/train.tsv` | `a53f2114831916c096b6c37d9e54da68cef4efdcdbd5ed46533601af972acf1d` |
| `qrels/test.tsv` | `0864bb985e0ca2367ba217977e72004d549054b2b06666ed9d4825ac7c21284c` |
