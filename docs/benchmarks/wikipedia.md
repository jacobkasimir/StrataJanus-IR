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
The completed main manifest reports zero skipped empty bodies.

## Workload and correctness

`configs/wikipedia_queries.json` contains a fixed set of 24 hand-written
queries, ranging from topical phrases to broad terms and one deliberately
unmatched term. These are synthetic benchmark inputs, not production queries
or measured user traffic. Each run uses BM25 `k1=1.2`, `b=0.75`, top 10,
five query repeats, one warm-up round, and seed 42.

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
- **Query latency** is collected after one warm-up round, for sequential
  searches over the fixed workload. Each trial reports its own p95; the
  summary below uses the median of those three trial-level p95 values.
- **File sizes** are logical file byte counts. `postings.bin` is the posting
  file for fixed32 and vb; JSON stores postings in `index.json`, so it has no
  separate posting-file size. Complete index size is the sum of every saved
  file, including metadata.
- **Memory** is absolute process RSS before, after, and at the sampled peak,
  sampled every 10 ms in separate runs. It is not an exact allocation size
  or a guaranteed peak; brief peaks can fall between samples.

Filesystem caches are not cleared. Fixed execution order (sizes ascending,
then formats JSON/fixed32/vb, with timing before memory) can introduce time and
order effects. Wikipedia article lengths vary, so document count alone does
not describe input text volume. All three storage formats reconstruct the
same in-memory posting representation; compressed storage does not imply
lower search-time memory. The benchmark does not measure Wikipedia relevance
metrics, and performance results provide no evidence about retrieval quality.

## Recorded results

The completed report `reports/benchmarks/wikipedia-scalability.json` records
status `complete`, all three requested sizes (10,000, 50,000, and 100,000),
and all three formats. Each size/format has three timing trials and one
separate memory run. The retry report
`reports/benchmarks/wikipedia-10k-retry.json` is a complete, separate 10,000
document run; the tooling smoke report `reports/benchmarks/wikipedia-smoke.json`
is complete at 1,000 documents. The main results below come only from the
complete main report. The accompanying
`reports/benchmarks/wikipedia-scalability.log` records two earlier attempts
that stopped during input fingerprinting with a file-read timeout, before
benchmark trials began; these failed attempts are not included in the results.

The environment was Python 3.14.9 on macOS 27.0.1 arm64 (`processor: arm`);
the report contains no more specific hardware model or hardware notes.
Defaults were used for BM25 (`k1=1.2`, `b=0.75`), 24 queries, top 10, five
query repetitions, and three timing trials. Times and sizes are medians or
file sizes from the first timing trial as applicable. Seconds are rounded to
two decimals; query values are milliseconds.

| Documents | Format | Ingest + build (s) | Save incl. validation (s) | Load/decode incl. validation (s) | BM25 init (ms) | Median trial p95 (ms) | Complete index (MiB) | Posting file (MiB) |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10,000 | JSON | 4.76 | 8.68 | 4.52 | 0.09 | 0.846 | 196.65 | — |
| 10,000 | fixed32 | 5.40 | 4.50 | 1.76 | 0.08 | 0.846 | 58.01 | 37.19 |
| 10,000 | vb | 5.96 | 5.39 | 4.09 | 0.08 | 0.841 | 37.08 | 10.17 |
| 50,000 | JSON | 14.62 | 29.13 | 16.52 | 1.01 | 2.697 | 653.60 | — |
| 50,000 | fixed32 | 14.16 | 13.94 | 4.80 | 0.34 | 2.684 | 167.61 | 122.49 |
| 50,000 | vb | 14.07 | 16.89 | 8.48 | 0.35 | 2.690 | 92.65 | 34.44 |
| 100,000 | JSON | 46.07 | 53.80 | 33.85 | 2.13 | 5.023 | 1,207.61 | — |
| 100,000 | fixed32 | 25.79 | 26.53 | 8.83 | 0.68 | 5.037 | 292.93 | 226.31 |
| 100,000 | vb | 26.08 | 31.51 | 16.32 | 0.64 | 4.996 | 149.35 | 64.07 |

The memory report is a sampled absolute RSS value. At 100,000 documents, the
timing-separate memory runs recorded these sampled peaks by phase (GiB):

| Format | Ingest + build | Save | Load/decode | BM25 init |
| --- | ---: | ---: | ---: | ---: |
| JSON | 2.28 | 2.34 | 2.84 | 2.43 |
| fixed32 | 2.27 | 2.55 | 3.01 | 2.14 |
| vb | 2.14 | 2.47 | 2.55 | 2.10 |

These are process RSS peaks sampled during the listed operation, not memory
increments attributable to that operation. The complete report retains exact
bytes, trial values, fingerprints, and the per-query results. The report's
source and workload fingerprints are preserved there. Earlier SciFact build
figures use a different corpus and timing scope; they should not be compared
directly with Wikipedia's JSONL ingestion-plus-build measurements.
