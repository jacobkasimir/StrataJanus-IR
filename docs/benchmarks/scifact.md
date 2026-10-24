# Performance benchmarks

## Scope

The benchmark measures:

- In-memory index construction.
- Index saving and loading.
- Posting and total index sizes.
- Warmed-up, sequential BM25 query latency.

Query timings exclude index loading, title lookup, and terminal output.

## Workload

Queries are sampled from SciFact training query IDs using a fixed seed.
The selected queries and raw latency observations are saved in the report.

## Run

    python scripts/benchmark_scifact.py --output reports/benchmarks/scifact-baseline.json

## Results

Add measured values from the generated report.

| Format | Total bytes | Posting bytes | Median save ms | Median load ms | Query p50 ms | Query p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| JSON | | Not isolated | | | | |
| fixed32 | | | | | | |
| vb | | | | | | |

## Conditions and limitations

- All formats reconstruct the same in-memory index.
- Filesystem caches are not cleared.
- Save functions do not explicitly call fsync.
- Measurements use one process and sequential queries.
- Timings depend on hardware and background activity.
- Retrieval quality and peak memory are evaluated separately.