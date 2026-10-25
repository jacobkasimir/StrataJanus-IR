# Vocabulary autocomplete

Autocomplete suggests terms from the vocabulary of an existing index. It does
not suggest documents or complete search queries. Each suggestion includes its
document frequency: the number of indexed documents containing that term.

## Prefix handling and ordering

The prefix is normalized with the same Unicode NFC normalization and
lowercasing used by the tokenizer. It must be nonempty and consist entirely of
characters matching the tokenizer's Unicode-aware `\w+` pattern. Empty
prefixes and prefixes containing whitespace or punctuation return no
suggestions; for example, `pro!` is rejected rather than tokenized to `pro`.
The Python API raises `TypeError` for a non-string prefix. The CLI always
receives a string positional argument.

Suggestions are ordered by descending document frequency, then ascending
Python string order for the term. `top_k` defaults to 10; zero returns no
suggestions and a negative value raises `ValueError`.

## Backends

- `TrieAutocomplete`: Python trie. For a prefix, it walks the matching
  subtree, gathers completions, and ranks them. It does not cache top
  suggestions at trie nodes, so a broad prefix can require scanning many
  terms.
- `SortedAutocomplete`: sorted vocabulary with `bisect` to find the prefix
  range, used as a baseline.
- `MarisaAutocomplete`: optional `marisa-trie` backend. It is available only
  when that package is installed; the benchmark includes it when available.

All three return the same suggestions for the same vocabulary and prefix.

## Run autocomplete

Build the SciFact JSON and fixed32 indexes first if they are not already
available. The command loads the fixed32 index and constructs the Python trie
when it starts:

```bash
python scripts/autocomplete_scifact.py prot --top-k 10
```

The command returns indexed terms matching `prot`, ordered by document
frequency and then term. `--top-k` is optional and defaults to 10.

## Benchmark

Run the benchmark with a new output path; it refuses to overwrite an existing
report:

```bash
python scripts/benchmark_autocomplete.py \
  --terms 100 \
  --repeats 5 \
  --warmup-rounds 1 \
  --top-k 10 \
  --seed 42 \
  --output reports/benchmarks/my-autocomplete-run.json
```

The script loads the SciFact fixed32 index, builds each available backend,
checks that their suggestions agree, then measures backend build time and
per-prefix suggestion latency after warmup. Its generated prefix workload
includes broad and narrow prefixes, case variants, an empty prefix, and a
prefix absent from the vocabulary. It reports latency percentiles and the
number of results for each sample. It does not measure end-to-end CLI startup
or index loading as part of suggestion latency, nor does it measure every
possible prefix or corpus.

### Recorded SciFact workload

The report `reports/benchmarks/scifact-autocomplete.json` records a run on the
35,954-term SciFact vocabulary with 100 sampled terms, 209 distinct prefixes,
five timed repetitions per prefix, one warmup round, `top_k=10`, and seed 42.
The environment was Python 3.14.9 on macOS 27 ARM64. The table reports build
time, p50 and p95 suggestion latency, and the measured process RSS change:

| Backend | Build ms | p50 ms | p95 ms | RSS delta |
| --- | ---: | ---: | ---: | ---: |
| Python trie | 63.191 | 0.010 | 0.549 | 16,547,840 bytes |
| Sorted/bisect | 3.228 | 0.009 | 0.237 | 114,688 bytes |
| marisa-trie | 15.950 | 0.010 | 0.453 | 2,195,456 bytes |

The sorted baseline performed well in this particular measured workload. These
SciFact measurements should not be generalized to other vocabularies or
prefix workloads. The RSS delta is process resident-set growth measured in a
child process after loading the vocabulary; it is not an exact measurement of
Python object memory.
