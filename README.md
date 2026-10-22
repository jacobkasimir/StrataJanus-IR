# StrataJanus-IR

**StrataJanus-IR** is a high-performance, multi-stage information retrieval (IR) engine built from first principles. It bridges classical algorithmic search data structures with modern neural retrieval and generative AI pipelines, evaluated against standard industry benchmarks.

Instead of relying on off-the-shelf search platforms like Elasticsearch or Lucene, this project implements low-level inverted indexing, ranking algorithms, dense vector retrieval, and LLM synthesis natively across five distinct architecture strata.

---

## 🏛️ System Architecture

The system is structured into five isolated strata. You can use, test, or deploy any stratum independently without relying on the full stack.
┌────────────────────────────────────────────────────────┐
│ Stratum 5: Domain Engine (SEC Filings / Quant Signals) │
├────────────────────────────────────────────────────────┤
│ Stratum 4: Generative RAG & Faithfulness Evaluator     │
├────────────────────────────────────────────────────────┤
│ Stratum 3: Learned Retrieval & Hybrid Ranking (LTR)    │
├────────────────────────────────────────────────────────┤
│ Stratum 2: Empirical IR Benchmarking & Metrics Suite   │
├────────────────────────────────────────────────────────┤
│ Stratum 1: Core Algorithmic Indexing & BM25 Engine     │
└────────────────────────────────────────────────────────┘

---

## 🛠️ Strata Specifications

* **Stratum 1: Core Engine (Zero Dependencies)**
  * Custom Inverted Index with variable-byte/delta compression codecs.
  * Optimized BM25 scoring algorithm implemented from scratch.
  * Prefix-matching Trie for auto-complete and Bloom Filter for fast vocabulary membership lookups.
  * Micro-benchmarked for build time, index compression ratio, and $p50/p95$ query latency.

* **Stratum 2: Empirical IR Evaluation**
  * Evaluated on standard IR benchmark datasets (**BEIR / MS MARCO / SciFact**).
  * Automated measurement of **nDCG@10**, **Recall@k**, and **MRR**.
  * Statistical significance testing between index and scoring model iterations.

* **Stratum 3: Learned Retrieval & Hybrid Ranking**
  * Hybrid retrieval pipeline fusing lexical BM25 scores with dense vector embeddings.
  * **Learning-to-Rank (LTR):** Trained a LightGBM LambdaMART model on custom engineered document/query features.
  * Fine-tuned cross-encoder reranker with full ablation studies comparing lexical, dense, and fused performance.

* **Stratum 4: Grounded LLM Layer**
  * Retrieval-Augmented Generation (RAG) with exact source citations and automated hallucination/faithfulness checks.
  * Evaluation using LLM-as-a-judge vs. ground-truth relevance labels.
  * Cost, token efficiency, and end-to-end latency profiling per query.

* **Stratum 5: Financial Signal Extraction (Optional Domain Adaptation)**
  * Domain-adapted ingestion pipeline for SEC filings ($10\text{-K}$, $10\text{-Q}$) and earnings transcripts to evaluate retrieved financial signals.

---
