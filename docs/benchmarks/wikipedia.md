# Wikipedia scalability benchmark

This benchmark measures StrataJanus-IR indexing and search over prepared
Wikipedia subsets. It is a performance experiment, not a production workload
or a retrieval-quality evaluation.

## Dataset and subset preparation

The source is the Hugging Face dataset `wikimedia/wikipedia`, configuration
`20231101.en`, split `train`. The completed subset manifest records dataset
revision `b04c8d1ceb2f5cd4588862100d08de323dccfbaa` and `datasets` 5.1.0. The
preparation script resolves a revision when run; pass the recorded revision
with `--revision` to request the same source snapshot. The benchmark report
embeds the manifest and fingerprints each JSONL input with SHA-256, then checks
those fingerprints before running.

Install the repository's pinned dependencies using its existing setup:

```bash
python -m pip install -r requirements.txt
```

The `requirements.txt` pins `datasets`, `huggingface_hub`, and `psutil` along
with the project's other tools. Prepare the default 10k, 50k, and 100k subsets
as follows (the output directory must not already exist):

```bash
python scripts/prepare_wikipedia_subsets.py \
  --sizes 10000 50000 100000 \
  --revision b04c8d1ceb2f5cd4588862100d08de323dccfbaa
```

For a small tooling smoke run, prepare a separate 1,000-document corpus and
write the benchmark report to a new path:

```bash
python scripts/prepare_wikipedia_subsets.py --sizes 1000 \
  --output-root data/processed/wikipedia-smoke \
  --revision b04c8d1ceb2f5cd4588862100d08de323dccfbaa
python scripts/benchmark_scalability.py \
  --corpus-root data/processed/wikipedia-smoke \
  --sizes 1000 \
  --timing-repeats 1 --memory-repeats 1 --query-repeats 2 \
  --output reports/benchmarks/my-wikipedia-smoke.json
```

The main experiment uses three timing trials and one separate memory trial
for each corpus size and index format:

```bash
python scripts/benchmark_scalability.py \
  --sizes 10000 50000 100000 \
  --formats json fixed32 vb \
  --timing-repeats 3 --memory-repeats 1 --query-repeats 5 \
  --top-k 10 --seed 42 \
  --output reports/benchmarks/my-wikipedia-scalability.json
```

The script refuses to overwrite an existing output report. Both scripts
support `--help` for the complete option list. Subset preparation requires
network access to resolve/download the source dataset; running the benchmark
uses the prepared local files.

## Canonical documents and nested selection

For each source record, the preparation script requires a string `title`, a
string `text`, and a non-null `id`. It skips bodies for which `text.strip()` is
empty. Each retained record is written as compact UTF-8 JSONL with the source
title and text, `metadata.source` set to `wikipedia`, and the source URL in
`metadata.url` (or an empty string when absent). Its external document ID is
`wikipedia-en:` followed by the source ID converted to a string. Duplicate
constructed IDs are rejected.

After skipping empty bodies, eligible records keep their original source
order. Each requested size takes the first N eligible records; the larger
subset therefore has the smaller subset as its prefix. This produces nested
subsets and makes size comparisons use the same initial source records. It
does not make them representative random samples. The manifest records the
selection rule, empty-body count, and SHA-256 of each exact serialized subset.
The completed main manifest reports zero skipped empty bodies and these
counts and fingerprints:

| Documents | Manifest path | SHA-256 |
| ---: | --- | --- |
| 10,000 | `10000/documents.jsonl` | `f5f0d43d10e3139ec94db0b29588b38886ae4a4653267401f5249aff099af1a3` |
| 50,000 | `50000/documents.jsonl` | `2e6e0c7954e95313d5314e549afd09ba720d76a5a0706fcb125bfa33f7b7eee2` |
| 100,000 | `100000/documents.jsonl` | `e464f46e4b587f5496e0379fd62b874e2632feff0b20de81860dba7abf1a90c1` |

These are manifest fingerprints, not a fresh verification of the current
local files. The complete reports show the harness matched these fingerprints
before starting their trials.

## Workload and correctness

`configs/wikipedia_queries.json` contains a fixed set of 24 hand-written
queries: topical phrases, broader terms such as `water`, `history`, and
`music`, and a deliberately unmatched term. This is an engineering workload
chosen to exercise varying posting-list sizes, not sampled or observed user
traffic. Each timing trial uses BM25 `k1=1.2`, `b=0.75`, top 10, five
measured sequential passes, one untimed warm-up pass, and seed 42.

For each size, the coordinator executes separate fresh Python subprocesses
for build/save and load/search. It runs timing and memory modes separately;
the memory measurement does not share a process with timing. The load process
initializes BM25 and searches the fixed query set sequentially. It fingerprints
the logical in-memory index and exact query results (including unrounded
scores). The coordinator checks that saved and reloaded indexes match and
that index and query fingerprints agree across all formats and repetitions
for a size. Thus JSON, fixed32, and vb are checked for equivalent reconstructed
indexes and ranked outputs.

## Measurement boundaries

- **Ingestion and construction** times reading JSONL records, parsing them,
  tokenizing, and building the in-memory index.
- **Save** times each format's save call, including its validation. The save
  functions do not explicitly `fsync` data to durable storage.
- **Load/decode** times loading the saved index, including validation. The
  entire index is decoded into Python memory.
- **BM25 initialization** is timed separately after load.
- **Query latency** times each `BM25.search()` call, including query
  tokenization, postings traversal, scoring, top-k selection, and creation of
  results. It excludes process startup, index loading, BM25 construction,
  title lookup, output printing, and result bookkeeping. The workload has 24
  queries × 5 rounds = 120 timed samples per trial. p50 and p95 use linear
  interpolation at `(n - 1) * p / 100` among those samples. Table p50/p95
  values are medians of the three independent trial-level p50/p95 values.
- **File sizes** are logical file byte counts. `postings.bin` is the posting
  file for fixed32 and vb; JSON stores postings in `index.json`, so it has no
  separate posting-file size. Complete index size is the sum of every saved
  file, including metadata.
- **Memory** is absolute process RSS before, after, and at the sampled peak
  for ingest/build, save, load, BM25 initialization, and the query batch.
  These are separate fresh-process runs from timing. RSS includes the process
  and its libraries, and is not memory attributable only to the phase. The
  sampler checks every 10 ms, so short-lived peaks may be missed; it is not an
  exact peak-allocation measurement.

Filesystem caches are not cleared, and there is no explicit `fsync`; load and
save times therefore reflect the observed cache and operating-system write
behavior, not cold-cache reads or durable-write latency. The fixed execution
order (sizes ascending, then JSON/fixed32/vb, timing before memory) can
introduce order effects. Article lengths vary, so document count alone does
not represent input text volume. All formats reconstruct the same in-memory
index and use the same BM25 implementation; compressed postings do not imply
lower search-time memory. No Wikipedia relevance labels are used, so these
performance measurements say nothing about retrieval quality.

## Recorded results

The completed report `reports/benchmarks/wikipedia-scalability.json` records
status `complete`, all three requested sizes (10,000, 50,000, and 100,000),
and all three formats. Each size/format has three timing trials and one
separate memory run. The retry report
`reports/benchmarks/wikipedia-10k-retry.json` is a complete, separate 10,000
document run; the tooling smoke report `reports/benchmarks/wikipedia-smoke.json`
is complete at 1,000 documents. The main results below come only from the
complete main report. The accompanying
`reports/benchmarks/wikipedia-scalability.log` records earlier attempts that
stopped while reading a subset for SHA-256 verification with
`TimeoutError: [Errno 60] Operation timed out`, before any build/save/load or
query trial began. Those attempts have no benchmark measurements and do not
establish corruption. The timeout source is unconfirmed. Do not disable
checksum verification to continue. A complete manifest alone does not prove
that files remain readable. Using local, non-synced storage is a possible
troubleshooting step, not a verified fix. The later complete reports establish
that the procedure did subsequently pass preflight and finish; they do not
explain the earlier I/O timeout.

The environment was Python 3.14.9 on macOS 27.0.1 arm64 (`processor: arm`);
the report contains no more specific hardware model or hardware notes.
Defaults were used for BM25 (`k1=1.2`, `b=0.75`), 24 queries, top 10, five
query repetitions, and three timing trials. Build, save, load, BM25-init, p50,
and p95 figures below are medians across the three independent timing trials;
size columns are logical file sizes from a timing trial. Times are rounded to
two decimals for seconds and three decimals for query milliseconds. Filesystem
cache state was not controlled, and trial-to-trial variability is material
for some build phases.

| Documents | Format | Ingest + build (s) | Save (s) | Load/decode (s) | BM25 init (ms) | Query p50 (ms) | Query p95 (ms) | Total index (MiB) | `postings.bin` (MiB) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10,000 | JSON | 4.76 | 8.68 | 4.52 | 0.09 | 0.413 | 0.846 | 196.65 | — |
| 10,000 | fixed32 | 5.40 | 4.50 | 1.76 | 0.08 | 0.414 | 0.846 | 58.01 | 37.19 |
| 10,000 | vb | 5.96 | 5.39 | 4.09 | 0.08 | 0.410 | 0.841 | 37.08 | 10.17 |
| 50,000 | JSON | 14.62 | 29.13 | 16.52 | 1.01 | 1.179 | 2.697 | 653.60 | — |
| 50,000 | fixed32 | 14.16 | 13.94 | 4.80 | 0.34 | 1.173 | 2.684 | 167.61 | 122.49 |
| 50,000 | vb | 14.07 | 16.89 | 8.48 | 0.35 | 1.179 | 2.690 | 92.65 | 34.44 |
| 100,000 | JSON | 46.07 | 53.80 | 33.85 | 2.13 | 2.094 | 5.023 | 1,207.61 | — |
| 100,000 | fixed32 | 25.79 | 26.53 | 8.83 | 0.68 | 2.064 | 5.037 | 292.93 | 226.31 |
| 100,000 | vb | 26.08 | 31.51 | 16.32 | 0.64 | 2.074 | 4.996 | 149.35 | 64.07 |

The fixed-width-to-vb `postings.bin` reduction, calculated from report byte
counts as `(fixed32 - vb) / fixed32`, was 72.64% at 10,000, 71.87% at 50,000,
and 71.69% at 100,000 documents. These are posting-file reductions, not total
index-directory reductions; vb vocabulary metadata is larger in these
reports. JSON postings are stored in `index.json`, so a posting-only JSON
comparison is unavailable.

The smaller vb posting files came with a load-time cost in these runs:
median vb load/decode took 4.09 s versus 1.76 s for fixed32 at 10,000
documents, 8.48 versus 4.80 s at 50,000, and 16.32 versus 8.83 s at
100,000. vb save was also slower than fixed32 in each size. This is an
observed tradeoff in these measurements, not a general format guarantee.

Across these completed nested sizes, median query p50 and p95 rise with size
in all three formats, while results remain close across formats because they
search the same reconstructed index. At 100,000 documents, trial-level build
times vary substantially (for example, JSON spans 26.07–53.28 s and vb spans
25.60–46.53 s), so the reported medians should not be read as precise capacity
limits. The dataset adds different article lengths at each prefix, and
filesystem caching, fixed format order, system load, and memory pressure are
possible contributors; the report does not isolate their effects.

Per-query evidence is consistent with posting work contributing to query
cost, without proving it is the only cause. For the fixed32 timing trials,
`history` (`w15`) visits 4,024, 16,952, and 32,439 postings at 10k, 50k, and
100k, with median individual latency across trial observations of 1.354,
5.744, and 11.095 ms. The lower-posting `volcanic eruption` (`w05`) visits
150, 351, and 591 postings and has corresponding medians of 0.062, 0.137,
and 0.219 ms. The unmatched query (`w24`) visits zero postings and remains
around 0.002 ms. These examples are observations from this fixed workload,
not general latency guarantees.

The memory report records one separate process per format and size. At
100,000 documents, the sampled absolute RSS peaks by phase were (GiB):

| Format | Ingest + build | Save | Load/decode | BM25 init | Query batch |
| --- | ---: | ---: | ---: | ---: | ---: |
| JSON | 2.28 | 2.34 | 2.84 | 2.43 | 2.49 |
| fixed32 | 2.27 | 2.55 | 3.01 | 2.14 | 2.15 |
| vb | 2.14 | 2.47 | 2.55 | 2.10 | 2.04 |

These are process RSS peaks sampled during the listed operation, not memory
increments attributable to that operation. The complete report retains exact
bytes, trial values, fingerprints, and the per-query results. The report's
source and workload fingerprints are preserved there. Earlier SciFact build
figures use a different corpus and timing scope; they should not be compared
directly with Wikipedia's JSONL ingestion-plus-build measurements.
