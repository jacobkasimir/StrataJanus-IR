# Index storage

stratajanus supports two uncompressed saved index formats: JSON and
fixed-width binary. Both load into the same in-memory `InvertedIndex` and
produce the same BM25 rankings.

## Build an index

    python scripts/build_scifact_index.py

## Search an existing index

    python scripts/search_scifact.py "immune response" --format json --top-k 5

## Saved files

- `index.json`: postings, document lengths, and external IDs.
- `tokenizer_config.json`: tokenizer settings.
- `manifest.json`: format version and counts.

## Safety checks

- Existing index directories are not overwritten.
- The loader checks format and tokenizer compatibility.
- Posting order, document references, and frequencies are validated.

The JSON index is loaded into memory for searching. Queries do not rebuild
the index from the processed corpus. The default format for
`search_scifact.py` is `json`; `scripts/load_scifact.py` is also a JSON-only
search command.

### JSON limitations

- The entire index is loaded into memory.
- JSON is a correctness baseline, not a compact storage format.
- Result titles are retrieved separately from the processed corpus.
- Failed saves may leave a partial directory.

## Fixed-width binary format

stratajanus supports a second storage format for the same inverted
index. Numerical data uses unsigned 32-bit little-endian integers.

### Files

- `postings.bin`: document ID and term-frequency pairs, 8 bytes per pair.
- `doc_lengths.bin`: 4 bytes per document.
- `vocabulary.json`: byte offsets and document frequencies.
- `doc_ids.json`: external document IDs in internal-ID order.
- `tokenizer_config.json`: tokenizer settings.
- `manifest.json`: format version and counts.

### Convert the JSON index

    python scripts/convert_index_to_binary.py

### Search the binary index

    python scripts/search_scifact.py "immune response" --format fixed32 --top-k 5

### Current limitations

- The complete index is reconstructed in memory.
- Numerical values must fit in unsigned 32-bit integers.
- This is uncompressed storage.
- The format is a baseline for later compression experiments.
