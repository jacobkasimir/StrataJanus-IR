# Text analysis and indexing

This page covers the tokenizer and inverted index used by BM25. For the
ranking formula and complete data flow, see [Architecture](architecture.md).

## Build an index

`build_index` consumes an ordered iterable of dictionaries. Each document
requires a nonempty string `doc_id` and string `title` and `text` fields;
additional fields are ignored. The title and body are joined with a newline,
then analyzed as one document. This boundary prevents the final title word
from merging with the first body word.

```python
from stratajanus.index.inverted import build_index

documents = [
    {"doc_id": "paper-1", "title": "Search systems", "text": "An inverted index."},
    {"doc_id": "paper-2", "title": "Retrieval", "text": "Search finds documents."},
]

index = build_index(documents)
print(index.document_count)                 # 2
print(index.average_document_length)        # mean token count
print(index.document_frequency("search"))   # documents containing the term
print(index.postings["search"])             # [(0, 1), (1, 1)]
print(index.internal_to_external[0])        # "paper-1"
```

Internal IDs start at zero and follow input order. A posting is
`(internal_id, term_frequency)`; each posting list is in ascending internal-ID
order. `doc_lengths[id]` counts all title and body tokens, and empty documents
remain represented with length zero. `document_frequency(term)` counts the
posting entries, not total occurrences. Empty input produces a valid empty
index. Invalid item types raise `TypeError`; invalid required fields and
duplicate IDs raise `ValueError`.

## Tokenization rules

`tokenize` applies Unicode NFC normalization, then Python's `str.lower()`,
then finds non-overlapping matches of the Unicode-aware regular expression
`\\w+`. Letters, digits, and underscores are included in tokens; punctuation
and other non-word characters separate tokens. For example, `COVID-19` becomes
`["covid", "19"]`, `3.14` becomes `["3", "14"]`, and `paper_123` remains one
token. Repeated tokens are preserved in order. Non-string input raises
`TypeError`; text with no word matches returns an empty list.

`TokenizerConfig` and `CONFIG` describe the active schema and settings.
`save_tokenizer_config(path)` writes formatted UTF-8 JSON and creates parent
directories. `verify_tokenizer_config(path)` raises `ValueError` if saved
settings differ from the active configuration.

## BM25 and command-line search

The [architecture page](architecture.md#bm25-retrieval) explains BM25's IDF,
parameters, query term handling, result ordering, and score meaning. A
processed SciFact collection can be searched using a saved index. Build it
once, then run queries against it:

```bash
python scripts/build_scifact_index.py
python scripts/search_scifact.py "evidence for a scientific claim" --format json --top-k 10
```

The build script reads the processed JSONL and saves the JSON index under
`data/indexes/scifact/`. The search script loads it and prints the result ID,
BM25 score, and title. To search the fixed-width binary format instead, first
run `python scripts/convert_index_to_binary.py` and pass `--format fixed32`.
Both formats require the SciFact preparation workflow described in
[dataset documentation](datasets/scifact.md). The storage layouts and
commands are described in [Index Storage](index_storage.md).

## API

See the [API reference](api.md) for generated documentation of
`InvertedIndex`, `build_index`, `TokenizerConfig`, `tokenize`, `BM25`, and
`SearchResult`.
