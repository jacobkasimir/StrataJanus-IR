# StrataJanus-IR

**A search engine built from scratch, layer by layer: inverted index → BM25 → hybrid retrieval → learned ranking → RAG, with every layer measured.**

![python](https://img.shields.io/badge/python-3.11+-blue) ![license](https://img.shields.io/badge/license-MIT-green) ![status](https://img.shields.io/badge/status-in%20development-orange)

---

## Why this project exists

Most search and RAG demos show that something works. StrataJanus-IR asks a harder question: **which layer of the stack actually improves results, by how much, and at what cost?**

The system is built in four strata. Each one is implemented by hand (no Elasticsearch, Lucene, or Whoosh for the core), evaluated on standard relevance benchmarks, and compared against the layer below it on both **quality** (nDCG, recall) and **cost** (latency, index size, dollars per query).

The name reflects the two-faced design: the *lexical* face (sparse, exact-match, fast) and the *semantic* face (dense, learned, expensive), looking at the same corpus.

---

## Results at a glance

> Replace the placeholders below with your measured numbers. Report the same dataset and the same hardware in every row.

**Dataset:** `<e.g., BEIR/SciFact>` | **Hardware:** `<CPU/GPU, RAM>` | **Queries:** `<N>`

| Stage | System | nDCG@10 | Recall@100 | MRR@10 | p50 latency | p95 latency | Cost / query |
|---|---|---|---|---|---|---|---|
| 1 | BM25 (from scratch) | – | – | – | – ms | – ms | $0 |
| 1 | BM25 (reference: `rank_bm25`) | – | – | – | – ms | – ms | $0 |
| 2 | Dense retrieval (`<model>`) | – | – | – | – ms | – ms | – |
| 2 | Hybrid (BM25 + dense, RRF) | – | – | – | – ms | – ms | – |
| 3 | Hybrid + LambdaMART reranker | – | – | – | – ms | – ms | – |
| 3 | Hybrid + cross-encoder reranker | – | – | – | – ms | – ms | – |
| 4 | RAG (answer generation) | see [RAG evaluation](#stage-4--rag-layer) | | | – ms | – ms | $– |

Differences are reported with 95% bootstrap confidence intervals and paired significance tests. See [`docs/evaluation.md`](docs/evaluation.md).

---

## Architecture

```
                         ┌──────────────────────────────┐
   Corpus ──► Tokenizer ─►│  Stage 1: Inverted index     │──► BM25 candidates ─┐
                         │  (compressed postings)       │                     │
                         └──────────────────────────────┘                     ▼
                         ┌──────────────────────────────┐              ┌─────────────┐
   Corpus ──► Embedder ──►│  Stage 2: Vector index       │──► Dense ───►│ Hybrid fuse │
                         │  (flat / HNSW)               │  candidates  │   (RRF)     │
                         └──────────────────────────────┘              └──────┬──────┘
                                                                              ▼
                         ┌──────────────────────────────┐              ┌─────────────┐
                         │  Stage 3: Rerankers          │◄─────────────│ Top-k pool  │
                         │  LambdaMART / cross-encoder  │              └─────────────┘
                         └───────────────┬──────────────┘
                                         ▼
                         ┌──────────────────────────────┐
                         │  Stage 4: RAG                │──► Cited answer
                         │  generation + faithfulness   │
                         └──────────────────────────────┘
```

---

## The four strata

### Stage 1: Core lexical engine

Everything here is written from scratch.

- **Inverted index** with positional postings.
- **BM25** ranking (tunable `k1`, `b`), validated against a reference implementation.
- **Index compression:** variable-byte and delta encoding of postings, with size and speed trade-offs measured.
- **Query processing:** boolean and ranked retrieval, with optional dynamic pruning (WAND or MaxScore) benchmarked against exhaustive scoring.
- **Auxiliary structures:** a trie for autocomplete and a Bloom filter for `<state its purpose here>`, each benchmarked against a standard-library baseline.

**Key questions answered:** How much does compression cost in latency? How much does pruning save, and does it change rankings?

### Stage 2: Dense and hybrid retrieval

- Embedding-based retrieval using `<embedding model>`.
- Vector index: exact flat search as the baseline, then an approximate index (HNSW) with a recall-vs-latency curve.
- **Hybrid fusion** of BM25 and dense scores using Reciprocal Rank Fusion, plus a weighted-score variant.

**Key questions answered:** On which query types does each retriever win? Is the hybrid gain worth the extra latency and memory?

### Stage 3: Learned ranking

- **LambdaMART** (LightGBM) trained on engineered features: BM25 score, dense similarity, query length, term coverage, document length, and so on.
- Optional **cross-encoder reranker**, fine-tuned or used off the shelf.
- Feature-importance analysis and **ablations** (remove one feature or stage at a time).

**Key questions answered:** What does reranking buy per extra millisecond? Which features matter? Where does the reranker make things worse?

### Stage 4: RAG layer

- Answer generation over retrieved passages with **inline citations**.
- **Faithfulness checks:** are the claims supported by the cited passages?
- **LLM-as-judge validation:** the judge is compared with a human-labeled sample of `<N>` answers, and agreement is reported (Cohen's kappa).
- Per-query token usage, latency, and cost.

**Key questions answered:** How often does the system hallucinate? How much do retrieval improvements propagate to answer quality? Can you trust the automatic judge?

---

## Evaluation methodology

- **Datasets:** `<BEIR SciFact>`, `<BEIR NFCorpus>`, `<MS MARCO subset>`. Links and licenses are in [`docs/datasets.md`](docs/datasets.md).
- **Metrics:** nDCG@10, Recall@k, MRR@10, MAP. Latency is reported as p50/p95/p99 over `<N>` queries after warm-up. Index size and build time are reported for every index.
- **Statistics:** paired bootstrap confidence intervals and significance tests across query-level scores.
- **Reproducibility:** fixed seeds, pinned dependencies, and one command per experiment. Results are saved as JSON under `results/` and tables are generated from them, never typed by hand.
- **No leakage:** LTR training and test queries are split strictly. Hyperparameters are tuned on a validation split only.

---

## Quickstart

```bash
git clone https://github.com/<your-username>/StrataJanus-IR.git
cd StrataJanus-IR

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 1. Download and prepare a dataset
python scripts/download_data.py --dataset scifact

# 2. Build the Stage 1 index
python -m stratajanus.index build --dataset scifact --compression vbyte

# 3. Search
python -m stratajanus.search "effect of vitamin D on bone density" --stage bm25 --top-k 5

# 4. Reproduce the results table
python scripts/run_eval.py --dataset scifact --stages all
```

> Stages 2 to 4 need extra dependencies (`pip install -e ".[dense,ltr,rag]"`). Stage 4 needs an LLM API key in `.env`. See `.env.example`.

---

## Repository structure

```
StrataJanus-IR/
├── src/stratajanus/
│   ├── tokenize/          # tokenization, stemming, stopwords
│   ├── index/             # inverted index, postings, compression
│   ├── rank/              # BM25, hybrid fusion, LTR, cross-encoder
│   ├── dense/             # embeddings, flat + HNSW vector index
│   ├── rag/               # generation, citations, faithfulness checks
│   ├── structures/        # trie, Bloom filter
│   └── eval/              # metrics, significance tests, latency harness
├── scripts/               # data download, experiment runners
├── benchmarks/            # micro-benchmarks vs. reference implementations
├── tests/                 # unit and property-based tests
├── results/               # raw experiment outputs (JSON)
├── docs/                  # design notes, evaluation details, write-up
└── README.md
```

---

## Testing

```bash
pytest -q                  # unit + property-based tests
pytest benchmarks/ --benchmark-only
```

- Index round-trip tests (compress → decompress equals original postings).
- BM25 scores checked against a reference implementation within tolerance.
- Metric implementations checked against `pytrec_eval` / `ir_measures`.
- Property-based tests (Hypothesis) for compression and the Bloom filter's false-positive bound.

---

## Findings and lessons

> Fill this in after running the experiments. Keep it honest, since negative results are valuable.

- *Example:* Hybrid retrieval improved nDCG@10 by `X` points over BM25 on `<dataset>`, but gave no significant gain on `<dataset>`.
- *Example:* Variable-byte compression cut index size by `X%` with a `Y%` latency cost.
- *Example:* The cross-encoder helped most on `<query type>` and hurt on `<query type>`, because `<reason>`.

## Limitations

- Evaluated on `<N>` datasets of `<size>`. Results may not transfer to web-scale corpora.
- The from-scratch engine is single-node and not optimized for concurrency.
- The LLM judge is validated on a small human-labeled sample.
- Dense retrieval and cross-encoder results depend on the chosen pretrained models.

## Roadmap

- [ ] Stage 1: index, BM25, compression, benchmarks
- [ ] Stage 2: dense retrieval, HNSW, hybrid fusion
- [ ] Stage 3: LambdaMART, cross-encoder, ablations
- [ ] Stage 4: RAG, faithfulness, judge validation
- [ ] Write-up in `docs/`
- [ ] Optional: Rust/C++ core for the index, with a latency comparison
- [ ] Optional: domain case study on financial filings (watch for lookahead leakage)

---

## References

- Robertson & Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond*
- Thakur et al., *BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of IR Models*
- Cormack et al., *Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods*
- Burges, *From RankNet to LambdaRank to LambdaMART: An Overview*
- Malkov & Yashunin, *Efficient and robust approximate nearest neighbor search using HNSW graphs*
- Manning, Raghavan & Schütze, *Introduction to Information Retrieval*

## License

MIT. See [`LICENSE`](LICENSE).

## Author

**`Jacob Tietz`**: [GitHub](https://github.com/<jacobkasimir>) · [LinkedIn](https://linkedin.com/in/<tietz-jacob>)
