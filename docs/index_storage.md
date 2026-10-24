# Index storage

stratajanus supports three saved index formats: JSON, fixed-width binary, and
variable-byte compressed postings. All formats load into the same in-memory
`InvertedIndex` and produce the same BM25 rankings.

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

All three formats are loaded and validated into memory for searching. Queries
do not rebuild the index from the processed corpus. The default format for
`search_scifact.py` is `json`; `scripts/load_scifact.py` is also a JSON-only
search command. The title lookup reads processed documents separately for
display and does not affect ranking.

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
- This format is uncompressed and serves as the comparison for vb postings.

## Compressed postings

The `vb` format compresses posting lists with document-ID gaps and unsigned
LEB128 integers. For each posting, the encoder writes the gap followed by the
term frequency. A posting list starts with its previous document ID set to
zero; each gap is the current ID minus the previous ID, so an initial document
ID of zero has a zero gap. Term frequencies are encoded directly, without
transformation.

Unsigned LEB128 stores seven payload bits per byte, least-significant group
first. The high bit is set when another byte follows. Every encoded value is
an unsigned 32-bit integer, so IDs, gaps, term frequencies, and document
lengths must fit the uint32 range. Document lengths are not compressed: they
remain four-byte unsigned little-endian integers in `doc_lengths.bin`.

The loader reads and decodes every posting list into the existing in-memory
index representation before BM25 search. Document lengths remain fixed-width
four-byte unsigned little-endian integers; they are not variable-byte encoded.

### Create and search the compressed index

    python scripts/compress_scifact_index.py

    python scripts/search_scifact.py "immune response" --format vb

### Files

- `postings.bin`: gap and term-frequency values encoded with unsigned LEB128.
- `doc_lengths.bin`: uncompressed four-byte document lengths.
- `vocabulary.json`: byte offset, byte length, and document frequency per
  posting list.
- `doc_ids.json`: external IDs in internal-ID order.
- `tokenizer_config.json` and `manifest.json`: tokenizer and format metadata.

### Measured SciFact sizes

These are logical byte counts from the SciFact index directories in this
checkout. Total size includes all data and metadata files in each directory.

| Format | Posting file | Total directory |
| --- | ---: | ---: |
| Fixed-width binary | 5,071,568 bytes | 7,740,869 bytes |
| Compressed postings (`vb`) | 1,389,292 bytes | 4,841,418 bytes |

The compressed posting file is smaller, while metadata and the unchanged
document-length file contribute to total directory size.

To calculate the posting-size reduction relative to the fixed-width format,
compare the compressed posting bytes with the fixed-width posting bytes:

$$
\mathrm{reduction}
=
100\left(
1-\frac{\mathrm{compressed\ posting\ bytes}}
{\mathrm{fixed\text{-}width\ posting\ bytes}}
\right)\%
$$

### Compressed-format limitations

- The complete index is decompressed into memory before searching.
- Values must fit in unsigned 32-bit integers.
- Document lengths remain uncompressed.
- Posting compression does not provide disk-backed or lazy query access.
