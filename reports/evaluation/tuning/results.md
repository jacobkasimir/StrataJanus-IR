# SciFact BM25 validation tuning results

Protocol: [`experiment-plan.md`](experiment-plan.md). All nine reports use the same validation queries, qrels, and fixed32 index.

Validated reports: split `validation`, 161 queries, index format `fixed32`.
Input SHA-256: queries `4a2f9389807c1ac7503ab3fe2357db782c0fd0d69405a12430f78b9083cb59fc`; qrels `3ef691aea3985486301e80c3e8c8e4d179736bd1e42510c8e2631b9253175493`; validation split `25a72119bec4e987570b05faf326d2aac6a2fb35285d2ea31a0a6b071023f73c`.

| k1 | b | Validation nDCG@10 | Recall@100 | MRR@10 |
|---:|---:|---:|---:|---:|
| 0.8 | 0.25 | 0.7064 | 0.9006 | 0.6764 |
| 0.8 | 0.75 | 0.7113 | 0.9130 | 0.6825 |
| *0.8* | *1.0* | *0.7114* | *0.9130* | *0.6847* |
| 1.2 | 0.25 | 0.7049 | 0.9006 | 0.6737 |
| 1.2 | 0.75 | 0.7096 | 0.9130 | 0.6801 |
| 1.2 | 1.0 | 0.7094 | 0.9130 | 0.6788 |
| 1.6 | 0.25 | 0.7042 | 0.9006 | 0.6703 |
| 1.6 | 0.75 | 0.7033 | 0.9130 | 0.6700 |
| 1.6 | 1.0 | 0.7007 | 0.9130 | 0.6690 |

The highest-scoring grid point under the predeclared rule was **k1=0.8, b=1.0** (nDCG@10 0.711433, Recall@100 0.913043, MRR@10 0.684659).

## Paired bootstrap comparison against the default

Compared per-query nDCG@10 for the grid winner (`k1=0.8`, `b=1.0`) against the default (`k1=1.2`, `b=0.75`) on the same 161 validation queries. The observed mean difference (winner minus default) was **+0.001810**. A paired percentile bootstrap with 100,000 resamples and seed `20261025` gave a 95% interval of **[-0.007122, +0.011445]**.

The interval includes zero, so this validation sample does not provide convincing evidence that the grid winner improves nDCG@10 over the default. Because the winner was chosen from this same grid and validation set, this comparison is exploratory and may overstate the gain. Retain the existing defaults (`k1=1.2`, `b=0.75`) unless an independent evaluation supports a change.

## Reports

- [`k1-0.8_b-0.25.json`](k1-0.8_b-0.25.json)
- [`k1-0.8_b-0.75.json`](k1-0.8_b-0.75.json)
- [`k1-0.8_b-1.0.json`](k1-0.8_b-1.0.json)
- [`k1-1.2_b-0.25.json`](k1-1.2_b-0.25.json)
- [`k1-1.2_b-0.75.json`](k1-1.2_b-0.75.json)
- [`k1-1.2_b-1.0.json`](k1-1.2_b-1.0.json)
- [`k1-1.6_b-0.25.json`](k1-1.6_b-0.25.json)
- [`k1-1.6_b-0.75.json`](k1-1.6_b-0.75.json)
- [`k1-1.6_b-1.0.json`](k1-1.6_b-1.0.json)
