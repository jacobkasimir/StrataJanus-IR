# API Reference

The package API is documented from its Python docstrings using
`mkdocstrings`. See [Quickstart](quickstart.md) for a runnable example,
[Indexing](indexing.md) for the data structures, and [Architecture](architecture.md)
for the ranking behavior.

## Tokenizer

::: stratajanus.text.tokenizer
    options:
      heading_level: 3
      members:
        - TokenizerConfig
        - CONFIG
        - tokenize
        - save_tokenizer_config
        - verify_tokenizer_config

## Inverted index

::: stratajanus.index.inverted
    options:
      heading_level: 3
      members:
        - InvertedIndex
        - build_index

## Index storage

JSON and fixed-width binary storage use separate modules and expose the same
save/load function names. Import them from their respective modules to choose
a format.

::: stratajanus.index.storage
    options:
      heading_level: 3
      members:
        - save_index
        - load_index

::: stratajanus.index.binary_storage
    options:
      heading_level: 3
      members:
        - save_index
        - load_index

::: stratajanus.index.compressed_storage
    options:
      heading_level: 3
      members:
        - save_index
        - load_index

::: stratajanus.index.codecs
    options:
      heading_level: 3
      members:
        - encode_uint
        - decode_uints

## BM25 retrieval

::: stratajanus.retrieval.bm25
    options:
      heading_level: 3
      members:
        - SearchResult
        - BM25

## Vocabulary autocomplete

::: stratajanus.retrieval.autocomplete
    options:
      heading_level: 3
      members:
        - Suggestion
        - TrieAutocomplete
        - SortedAutocomplete
        - MarisaAutocomplete

## Benchmark utility

::: stratajanus.evaluation.performance
    options:
      heading_level: 3
      members:
        - percentile
        - latency_summary
        - benchmark_queries

## SciFact workflow scripts

These functions expose the reusable portions of the dataset workflow. The
scripts can also be invoked from the repository root as shown on the
[home page](index.md).

### Download

::: scripts.download_scifact
    options:
      heading_level: 4
      members:
        - main

### Search saved JSON index

::: scripts.load_scifact
    options:
      heading_level: 4
      members:
        - main

### Prepare processed data

::: scripts.prepare_scifact
    options:
      heading_level: 4
      members:
        - read_jsonl
        - require_id
        - require_text
        - prepare_metadata
        - write_jsonl_row
        - convert_documents
        - convert_queries
        - convert_qrels
        - main

### Validate an index

::: scripts.index_scifact
    options:
      heading_level: 4
      members:
        - read_jsonl
        - main

### Search SciFact

::: scripts.search_scifact
    options:
      heading_level: 4
      members:
        - main

### Build and convert indexes

`build_scifact_index.py` creates the JSON index. `convert_index_to_binary.py`
creates the fixed-width binary variant from the saved JSON index, and
`compress_scifact_index.py` writes the compressed-postings variant from the
fixed-width index; these
commands are documented on the [Index Storage](index_storage.md) page.
