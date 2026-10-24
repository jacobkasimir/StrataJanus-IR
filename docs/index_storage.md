# Index storage

stratajanus currently saves its inverted index as uncompressed JSON.

## Build an index

    python scripts/build_scifact_index.py

## Search an existing index

    python scripts/load_scifact.py "immune response" --top-k 5

## Saved files

- `index.json`: postings, document lengths, and external IDs.
- `tokenizer_config.json`: tokenizer settings.
- `manifest.json`: format version and counts.

## Safety checks

- Existing index directories are not overwritten.
- The loader checks format and tokenizer compatibility.
- Posting order, document references, and frequencies are validated.

The saved index is loaded into memory for searching. Queries do not rebuild
the index from the processed corpus.

## Current limitations

- The entire index is loaded into memory.
- JSON is a correctness baseline, not a compact storage format.
- Result titles are retrieved separately from the processed corpus.
- Failed saves may leave a partial directory.
