# StrataJanus-IR

**StrataJanus-IR** is an educational search engine built from first principles in Python. It uses a deterministic tokenizer, an inverted index, and BM25 ranking to search documents.

The project currently uses the BEIR-formatted SciFact dataset as its example corpus. An index can be saved as readable JSON, fixed-width binary, or with gap-encoded variable-byte postings.

> **Status:** StrataJanus-IR implements lexical search, vocabulary autocomplete, SciFact retrieval-quality evaluation, and a Wikipedia scalability benchmark through 100,000 documents. Dense/hybrid retrieval, learning to rank, and RAG are not implemented.

## Features

- **Deterministic tokenization:** Unicode NFC normalization, lowercasing, and regex-based token extraction.
- **Inverted indexing:** Posting lists containing internal document IDs and term frequencies.
- **BM25 ranking:** Search results ranked using term frequency, document frequency, and document-length normalization.
- **Vocabulary autocomplete:** Suggests indexed terms from typed prefixes. See the [autocomplete guide](docs/autocomplete.md) for behavior and the SciFact benchmark.
- **Persistent index storage:** JSON, fixed-width binary, and gap-encoded variable-byte postings.
- **Retrieval evaluation:** SciFact validation and held-out test metrics; see [retrieval evaluation](docs/retrieval-evaluation.md) for protocols and reports.
- **Validation:** Checks for malformed indexes and incompatible tokenizer configurations.
- **Automated tests:** Cover tokenization, indexing, BM25, autocomplete, retrieval metrics, and storage validation.
- **Performance benchmarks:** SciFact baselines and a Wikipedia scalability benchmark through 100,000 documents. See [Wikipedia scalability](docs/benchmarks/wikipedia.md) for the workflow, measurement limits, and results.

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
JSON, fixed-width, or compressed-postings storage
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

Install the pinned dependencies used by the SciFact scripts, tests, and documentation:

```bash
python -m pip install -r requirements.txt
```

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

**This format is not compressed.** It serves as the fixed-width comparison for the compressed-postings format.

If the binary index directory already exists, the conversion script refuses to overwrite it.

## Create the compressed-postings index

After creating the fixed-width index, encode posting document IDs as gaps and
unsigned variable-byte integers:

```bash
python scripts/compress_scifact_index.py
```

This writes `data/indexes/scifact-vb/` and checks that loading it reconstructs
the same index. Posting lists are compressed; document lengths remain
fixed-width unsigned 32-bit integers. The loader decodes the full index into
memory.

## Search SciFact

Search the saved JSON index:

```bash
python scripts/search_scifact.py "immune response" --format json --top-k 5
```

Search the saved binary index:

```bash
python scripts/search_scifact.py "immune response" --format fixed32 --top-k 5
```

Search the compressed-postings index:

```bash
python scripts/search_scifact.py "immune response" --format vb --top-k 5
```

For the same query, all three formats should return the same ranked document IDs and BM25 scores.

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

Run the index-storage tests:

```bash
python -m pytest tests/test_index_storage.py tests/test_binary_storage.py -v
```

The tests cover tokenization, index construction, BM25, dataset preparation,
storage round trips, compression codecs, and malformed index validation.

## Run the SciFact benchmark

With processed SciFact data present, generate a new report at a path that does
not already exist:

```bash
python scripts/benchmark_scifact.py --output reports/benchmarks/my-run.json
```

The script measures construction, save/load, logical file sizes, and warmed,
sequential query latency for all three formats. It does not overwrite reports.
See [the benchmark documentation](docs/benchmarks/scifact.md) for its workload,
timing boundaries, and existing report details.

## Documentation

The detailed documentation is maintained with MkDocs.

Start the local documentation server:

```bash
mkdocs serve
```

Open the local URL shown in your terminal.

To build the documentation site and treat warnings as errors:

```bash
mkdocs build --strict
```

The README is a quick-start guide. The [MkDocs pages](docs/index.md) cover
architecture, indexing, storage formats, autocomplete, retrieval evaluation,
dataset preparation, benchmarks, and the public API.

## Repository structure

```text
src/stratajanus/
├── text/                       Tokenization
├── index/                      Inverted index and storage formats
├── retrieval/                  BM25 ranking and vocabulary autocomplete
└── evaluation/                 Benchmarks, SciFact data, and retrieval metrics

scripts/                       Dataset and index commands
tests/                         Automated tests
docs/                          MkDocs documentation source
data/                          Local datasets and generated indexes
```

The `data/` directory contains downloaded and generated files and should not be committed to Git.

## Current limitations

- Search is lexical: different words with similar meanings do not automatically match.
- BM25 retrieval quality has been evaluated on a fixed SciFact validation split. The parameter-selection protocol and results are documented in [retrieval evaluation](docs/retrieval-evaluation.md); official test judgments were not used for tuning.
- Each search command loads the saved index into memory. The current implementation does not search postings directly from disk.
- The `fixed32` index is uncompressed; the `vb` format compresses postings while document lengths remain fixed-width and the loader expands postings into memory.
- The Wikipedia benchmark records sampled process RSS and warmed sequential query latency; it is not a concurrent throughput or retrieval-quality evaluation. See [Wikipedia scalability](docs/benchmarks/wikipedia.md#measurement-boundaries) for the limits.
- Result-title lookup may read the processed corpus separately.
- Dense retrieval, learning to rank, and grounded answer generation are not yet implemented.

## Roadmap

- [x] Add document-ID gap encoding and variable-byte compression for postings.
- [x] Add an initial SciFact benchmark for index size, build/save/load time, and warmed query latency.
- [ ] Compare retrieval and storage behavior with a standard implementation.
- [x] Benchmark index construction, storage, loading, and warmed queries on nested Wikipedia subsets through 100,000 documents.
- [x] Evaluate retrieval quality using SciFact validation relevance labels.
- [x] Add SciFact vocabulary autocomplete with trie, sorted-list, and optional marisa-trie backends.
- [ ] Add dense and hybrid retrieval.
- [ ] Train and evaluate a learning-to-rank model.
- [ ] Add grounded answer generation with citations.

## Dataset and licensing

SciFact is a third-party dataset distributed through BEIR. Check its applicable terms before redistributing the dataset or derived artifacts.

Add the stratajanus project's software license here once you have selected one.
