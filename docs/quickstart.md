# Quickstart

This page gets the documentation project running and gives you a small, dependency-free BM25 example you can execute with Python 3.13 or newer.

!!! note "Repository status"
    The repository currently contains the project documentation and BEIR/SciFact data-loading scripts, but it does not yet expose a package-level `BM25Index` class. The example below is self-contained so you can run and inspect the core ranking idea today. When the engine API is published, this example can be replaced with the package import and its equivalent calls.

## 1. Create a virtual environment

From the project root, create and activate a local environment. This keeps tools installed for the project separate from your system Python.

```bash
python3.13 --version
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

The repository's pinned `requirements.txt` includes documentation, dataset, and ML tooling; those optional tools are not needed for the standard-library example below. To install the documented project toolchain, run:

```bash
python -m pip install -r requirements.txt
```

## 2. Index three documents and search

Save this as `quickstart.py` and run `python quickstart.py`. It uses a small in-memory inverted index and BM25 scorer. The simplified tokenizer lowercases text and splits on whitespace so the mechanics stay visible.

```python
from collections import Counter, defaultdict
from math import log


class BM25Index:
    """Small, in-memory BM25 index for learning and experimentation."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.documents: dict[str, str] = {}
        self.lengths: dict[str, int] = {}
        self.postings: dict[str, dict[str, int]] = defaultdict(dict)

    @staticmethod
    def tokenize(text: str) -> list[str]:
        return text.lower().split()

    def add_document(self, doc_id: str, text: str) -> None:
        terms = self.tokenize(text)
        counts = Counter(terms)
        self.documents[doc_id] = text
        self.lengths[doc_id] = len(terms)
        for term, frequency in counts.items():
            self.postings[term][doc_id] = frequency

    def search(self, query: str, limit: int = 10) -> list[tuple[str, float]]:
        n_docs = len(self.documents)
        if n_docs == 0:
            return []

        average_length = sum(self.lengths.values()) / n_docs
        scores: Counter[str] = Counter()
        for term in self.tokenize(query):
            term_postings = self.postings.get(term, {})
            if not term_postings:
                continue

            doc_frequency = len(term_postings)
            idf = log(1 + (n_docs - doc_frequency + 0.5) / (doc_frequency + 0.5))
            for doc_id, frequency in term_postings.items():
                length_ratio = self.lengths[doc_id] / average_length
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length_ratio
                )
                scores[doc_id] += idf * (
                    frequency * (self.k1 + 1) / denominator
                )

        return sorted(scores.items(), key=lambda result: result[1], reverse=True)[:limit]


index = BM25Index()
index.add_document("doc-1", "python information retrieval search")
index.add_document("doc-2", "retrieval systems use an inverted index")
index.add_document("doc-3", "python makes a clear teaching language")

for doc_id, score in index.search("python retrieval"):
    print(f"{doc_id}: {score:.3f} — {index.documents[doc_id]}")
```

Documents that match more query terms generally score higher. BM25's frequency saturation and length normalization keep long documents and repeated terms from dominating solely because they contain more words.

!!! tip "Performance"
    This teaching index is in memory and rebuilds its collection statistics during a search. It is intended for a tiny example, not a large corpus or persistent production index.

## 3. Preview the documentation

If the documentation dependencies are installed, start MkDocs Material's live preview:

```bash
mkdocs serve
```

Then open the local URL printed by MkDocs. The site navigation is configured in `mkdocs.yml`.
