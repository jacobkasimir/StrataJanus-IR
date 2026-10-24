# StrataJanus-IR

**StrataJanus-IR** is an educational search engine built from first principles in Python. It uses a deterministic tokenizer, an inverted index, and BM25 ranking to search documents.

The project currently uses the BEIR-formatted SciFact dataset as its example corpus. An index can be saved as readable JSON or in an uncompressed, fixed-width binary format.

> **Status:** stratajanus currently supports lexical search. Compression, retrieval evaluation, autocomplete, dense retrieval, and RAG are planned but not yet implemented.

## Features

- **Deterministic tokenization:** Unicode NFC normalization, lowercasing, and regex-based token extraction.
- **Inverted indexing:** Posting lists containing internal document IDs and term frequencies.
- **BM25 ranking:** Search results ranked using term frequency, document frequency, and document-length normalization.
- **Persistent index storage:** JSON and fixed-width binary formats.
- **Validation:** Checks for malformed indexes and incompatible tokenizer configurations.
- **Automated tests:** Tests for tokenization, indexing, ranking, and index-storage round trips.

## How it works

```text
BEIR SciFact corpus
       ↓
Canonical document format
       ↓
Tokenizer
       ↓
Inverted index
       ↓
JSON or fixed-width binary storage
       ↓
Load saved index
       ↓
BM25 search results
```

The inverted index maps each token to the documents containing it:

```text
"search" → [(0, 2), (3, 1)]
```

Each pair is:

```text
(internal_document_id, term_frequency)
```

The index also stores document lengths and a mapping from internal integer IDs back to the original SciFact document IDs.

## Requirements

- **Python 3.14**, the version currently used for development and testing.
- Internet access to download SciFact, unless you already have the dataset locally.
- A terminal for running the setup and search commands.

Other Python versions have not yet been tested.

## Installation

Clone this repository, open a terminal in its root directory, and create a virtual environment:

```bash
python3.14 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project in editable mode:

```bash
python -m pip install -e .
```

Install the development tools used in this guide if they are not already declared by your project dependencies:

```bash
python -m pip install pytest mkdocs
```

> If `mkdocs.yml` enables plugins such as `mkdocstrings`, install their dependencies as specified in `pyproject.toml` or your documentation setup. `mkdocs` alone does not install every possible plugin.

After activating the virtual environment, `python` should refer to the environment's Python 3.14 interpreter. Check with:

```bash
python --version
```

## Prepare the SciFact dataset

Download the BEIR-formatted SciFact dataset:

```bash
python scripts/download_scifact.py
```

Convert the downloaded corpus, queries, and relevance judgments into stratajanus's canonical format:

```bash
python scripts/prepare_scifact.py
```

Processed files are written under:

```text
data/processed/scifact/
```

The processed dataset includes:

- `documents.jsonl`: canonical documents.
- `queries.jsonl`: canonical queries.
- `doc_ids.jsonl`: mapping between internal and original document IDs.
- `qrels/`: relevance judgments, separated by available dataset split.
- `manifest.json`: dataset-processing information and counts.

The preparation script refuses to overwrite an existing processed-data directory. If the data is already prepared, skip this step.

## Build the JSON index

Build and save an inverted index:

```bash
python scripts/build_scifact_index.py
```

The saved files are written under:

```text
data/indexes/scifact/
```

The JSON format is intended to be readable and easy to inspect. It is a correctness baseline, not a compact production format.

If the index directory already exists, the build script refuses to overwrite it.

## Create the fixed-width binary index

After building the JSON index, create a binary copy:

```bash
python scripts/convert_index_to_binary.py
```

The binary index is written under:

```text
data/indexes/scifact-fixed32/
```

The fixed-width format stores:

- Internal document IDs as unsigned 32-bit integers.
- Term frequencies as unsigned 32-bit integers.
- Document lengths as unsigned 32-bit integers.

Document IDs and term frequencies together occupy **eight bytes per posting**. Metadata, vocabulary entries, and external document IDs remain in JSON files.

**This format is not compressed.** It provides a baseline for future compression experiments.

If the binary index directory already exists, the conversion script refuses to overwrite it.

## Search SciFact

Search the saved JSON index:

```bash
python scripts/search_scifact.py "immune response" --format json --top-k 5
```

Search the saved binary index:

```bash
python scripts/search_scifact.py "immune response" --format fixed32 --top-k 5
```

For the same query, both formats should return the same ranked document IDs and BM25 scores.

The search script loads the selected saved index. It does **not** rebuild the index for every query. It may read the processed documents separately to display titles.

Try another query:

```bash
python scripts/search_scifact.py "protein expression" --format fixed32 --top-k 10
```

## Run the tests

Run the complete test suite:

```bash
python -m pytest -v
```

Run only the index-storage tests:

```bash
python -m pytest tests/test_index_storage.py tests/test_binary_storage.py -v
```

The tests cover the tokenizer, inverted index, BM25 scoring, save/load round trips, and validation of incorrect index files.

## Documentation

The detailed documentation is maintained with MkDocs.

Start the local documentation server:

```bash
mkdocs serve
```

Open the local URL shown in your terminal.

To build the documentation site without starting a server:

```bash
mkdocs build
```

The README is a quick-start guide. The MkDocs site is intended to contain the more detailed architecture, storage-format, and API documentation.

## Repository structure

```text
src/stratajanus/
├── text/                       Tokenization
├── index/                      Inverted index and storage formats
└── retrieval/                  BM25 ranking

scripts/                       Dataset and index commands
tests/                         Automated tests
docs/                          MkDocs documentation source
data/                          Local datasets and generated indexes
```

The `data/` directory contains downloaded and generated files and should not be committed to Git.

## Current limitations

- Search is lexical: different words with similar meanings do not automatically match.
- Search results are ranked with BM25, but retrieval quality has not yet been formally reported using SciFact relevance judgments.
- Each search command loads the saved index into memory. The current implementation does not search postings directly from disk.
- The binary index is fixed-width and uncompressed.
- Result-title lookup may read the processed corpus separately.
- Compression, autocomplete, dense retrieval, learning to rank, and grounded answer generation are not yet implemented.

## Roadmap

- [ ] Add document-ID gap encoding and variable-byte compression.
- [ ] Benchmark index size, build time, and query latency.
- [ ] Evaluate retrieval quality using relevance labels.
- [ ] Add autocomplete using a trie or another measured approach.
- [ ] Add dense and hybrid retrieval.
- [ ] Train and evaluate a learning-to-rank model.
- [ ] Add grounded answer generation with citations.

## Dataset and licensing

SciFact is a third-party dataset distributed through BEIR. Check its applicable terms before redistributing the dataset or derived artifacts.

Add the stratajanus project's software license here once you have selected one.