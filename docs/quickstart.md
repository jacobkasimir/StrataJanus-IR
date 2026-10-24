# Quickstart

This guide uses the implemented package API with a tiny in-memory collection.
For a full SciFact workflow, see the [home page](index.md).

## Install

stratajanus requires Python 3.13 or newer. From the repository root:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r requirements.txt
```

The package itself uses the standard library. The pinned requirements include
the tools needed for tests, SciFact scripts, and documentation.

## Build an index and search

```python
from stratajanus.index.inverted import build_index
from stratajanus.retrieval.bm25 import BM25

documents = [
    {
        "doc_id": "paper-1",
        "title": "Search systems",
        "text": "An inverted index supports retrieval.",
    },
    {
        "doc_id": "paper-2",
        "title": "Scientific evidence",
        "text": "Evidence supports a scientific claim.",
    },
]

index = build_index(documents)
ranker = BM25(index)

for result in ranker.search("inverted retrieval"):
    document = documents[result.internal_id]
    print(result.doc_id, result.score, document["title"])
```

`build_index` assigns internal IDs in input order and stores the original IDs
separately. The result score is an uncalibrated BM25 ranking score. Repeated
query terms count once; ties preserve input order. See the [indexing guide](indexing.md)
for the tokenizer and posting format, and the [API reference](api.md) for all
public package and script APIs.

## Search SciFact

After installing dependencies, fetch and prepare the dataset, then run the
search script:

```bash
python scripts/download_scifact.py
python scripts/prepare_scifact.py
python scripts/build_scifact_index.py
python scripts/search_scifact.py "evidence for a scientific claim" --format json --top-k 10
```

Build the JSON index once after preparing the corpus. The search CLI loads
the saved index instead of rebuilding it. To use fixed-width binary, convert
the JSON index with `python scripts/convert_index_to_binary.py`, then pass
`--format fixed32` to `search_scifact.py`. The data download, conversion, and
index files are written under ignored `data/` directories. See
[Index Storage](index_storage.md) for both formats and [SciFact data](datasets/scifact.md)
for dataset preparation details.

## Tests and documentation preview

```bash
python -m pytest
mkdocs serve
```

MkDocs Material and `mkdocstrings` are included in the pinned
`requirements.txt` toolchain. To build a static documentation site, run
`mkdocs build --strict`.
