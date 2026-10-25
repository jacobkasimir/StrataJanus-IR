# Vocabulary autocomplete

## Purpose

Suggest indexed SciFact vocabulary terms from a typed prefix.
Autocomplete does not rank or return documents.

## Ranking rule

Suggestions are ranked by descending document frequency.
Ties are resolved by ascending term order.

## Implementations

- Python trie.
- Sorted vocabulary with binary search.
- Optional marisa-trie comparison.

## Normalization

Prefixes use the tokenizer's Unicode NFC normalization and
lowercasing. Invalid or empty prefixes return no suggestions.

## Commands

    python scripts/autocomplete_scifact.py prot --top-k 10

    python scripts/benchmark_autocomplete.py \
      --output reports/benchmarks/scifact-autocomplete.json

## Results

Add measured results from a completed benchmark report.

## Limitations

- The Python trie does not cache top suggestions per node.
- Broad prefixes may require examining many terms.
- Autocomplete is constructed when the demo command starts.
- RSS deltas are approximate.