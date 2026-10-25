# SciFact BM25 validation tuning plan

This plan is recorded before running the parameter grid.

## Frozen grid

| k1 | b |
|---:|---:|
| 0.8 | 0.25 |
| 0.8 | 0.75 |
| 0.8 | 1.0 |
| 1.2 | 0.25 |
| 1.2 | 0.75 |
| 1.2 | 1.0 |
| 1.6 | 0.25 |
| 1.6 | 0.75 |
| 1.6 | 1.0 |

The default is k1=1.2, b=0.75.

## Evaluation protocol

Run each combination with `scripts/evaluate_scifact.py` using `--split validation` and `--format fixed32`. Save one JSON report per combination under this directory. Do not use the official test split.

## Decision rule

Choose the combination with the highest validation nDCG@10. Break ties by highest validation Recall@100, then highest validation MRR@10. If all three metrics remain tied, choose the defaults k1=1.2, b=0.75.

Before comparing metrics, require every report to have split `validation`, the same query count, identical queries and qrels SHA-256 fingerprints, and index format `fixed32`. Across reports, only k1 and b should vary.
