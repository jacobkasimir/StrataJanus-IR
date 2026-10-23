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

## BM25 retrieval

::: stratajanus.retrieval.bm25
    options:
      heading_level: 3
      members:
        - SearchResult
        - BM25

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

### Load and inspect source splits

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
        - read_documents
        - main
