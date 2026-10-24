# Performance benchmarks

## Scope

`scripts/benchmark_scifact.py` measures index construction, saving and loading
for JSON, fixed32, and vb, logical file sizes, and warmed sequential BM25 query
latency. It also checks that each loaded format returns the same ranked IDs and
scores for the selected workload. This is an initial performance benchmark;
it does not evaluate retrieval quality, peak memory, concurrent throughput, or
large-corpus scalability.

## Run

Prepare SciFact first, then write to a report path that does not already exist:

```bash
python scripts/benchmark_scifact.py --output reports/benchmarks/my-run.json
```

The default output is `reports/benchmarks/scifact-baseline.json`; an existing
destination causes the script to stop rather than overwrite it. Defaults are
100 requested queries, 5 query rounds, 3 build/save/load repetitions, one
warm-up round, `top_k=10`, and seed 42. Counts and top-k can be adjusted with
`--queries`, `--query-repeats`, `--index-repeats`, `--warmup-rounds`, `--top-k`,
and `--seed`. `--hardware-notes` records an optional environment description.

## Workload and timing

The workload comes from canonical `queries.jsonl`, restricted to query IDs
present in canonical training `qrels/train.tsv`. The script sorts those IDs,
then samples up to the requested count with `random.Random(seed)`. The chosen
IDs and text are included in the report. Before measurement, every selected
query is searched once for each warm-up round. Each measured round shuffles the
workload with a seeded generator, then searches sequentially.

Each latency sample times only `BM25.search(query_text, top_k=...)` using
`perf_counter_ns`. Ranker initialization, index loading, result bookkeeping,
title lookup, and printing are outside this interval. p50 and p95 use linear
interpolation at `(n - 1) * p / 100` over sorted samples.

Construction time covers `build_index`. Save and load durations cover the
complete storage functions, including their validation, serialization or
decoding, and file operations. Loading reconstructs and validates the complete
in-memory index in every format; vb postings are not queried lazily from disk.
The JSON format stores postings in JSON, so its posting-only byte count is not
isolated in the report. For binary formats, `postings.bin` is the posting-only
size. Total size is the sum of logical file sizes under the format's index
directory, including metadata.

The benchmark does not clear filesystem caches. Save timings end after the
save function returns and files are closed; no explicit `fsync` is performed,
so they do not establish durable-write latency. Queries are sequential rather
than a concurrent throughput test. The report records Python/platform and
machine fields, optional hardware notes, configuration, tokenizer settings,
SHA-256 fingerprints for required input files, and source files.

## Existing reports

The repository contains [scifact-run-2.json](../../reports/benchmarks/scifact-run-2.json),
a 100-query report with 5 measured rounds per query (500 observations per
format), 3 index repetitions, one warm-up round, `top_k=10`, and seed 42. It
records 5,183 documents and 35,954 terms. The following values are copied from
that report; timings are medians for save/load and interpolated percentiles
for query latency. Byte counts are logical file sizes.

| Format | Total bytes | Posting bytes | Median save ms | Median load ms | Query p50 ms | Query p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| JSON | 26,845,586 | Not isolated | 1,070.903 | 381.554 | 3.882 | 6.954 |
| fixed32 | 7,740,869 | 5,071,568 | 426.127 | 171.048 | 3.882 | 6.948 |
| vb | 4,841,418 | 1,389,292 | 581.838 | 328.415 | 3.892 | 6.966 |

These are observations from one report, not repeated independent runs or
confidence intervals. They are a small SciFact baseline and do not establish
scalability or general performance rankings. See the report JSON for build
time, raw latency samples, environment details, and fingerprints. The
`scifact-baseline.json` and `scifact-smoke.json` files are also present; the
smoke report uses a smaller workload and should not be compared as if it had
the same measurement precision.
