# StrataJanus-IR

StrataJanus-IR is an educational information retrieval engine built as five cooperating strata. It follows a search request from a collection of documents through ranking, evaluation, reranking, and (optionally) grounded answer synthesis.

Information retrieval (IR) is the study and practice of finding useful items in a collection in response to a user's need. A web search engine is a familiar example, but the same ideas apply to scientific papers, legal cases, and financial filings.

## Why build the core from scratch?

The core ranking path is designed to use Python's standard library rather than hiding its behavior behind a heavyweight search service. That makes the important structures visible: token counts, postings lists, document lengths, and ranking scores. Students can inspect and change the algorithm, then connect its results to standard benchmarks.

This is a learning and research trade-off. A small transparent implementation is easier to understand; production search systems add optimized storage, distributed indexing, language analysis, and operational safeguards that are outside the core teaching goal.

!!! note "Concept: an inverted index"
    A library catalog can be thought of as a list of books and the words they contain. An inverted index flips that view: for each word, it stores the documents where the word appears. A query can then visit relevant postings instead of scanning every document.

## The five strata

| Stratum | Responsibility | What you learn |
| --- | --- | --- |
| 1. Core inverted index | Index documents and rank query results with BM25 | Tokenization, postings lists, term statistics, and relevance scoring |
| 2. Benchmark suite | Load BEIR-style corpora, queries, and relevance judgments; measure NDCG@10 and Recall@k | Reproducible evaluation and the difference between ranking quality and coverage |
| 3. Hybrid LTR | Extract ranking features and rerank candidates with Learning to Rank (including LambdaMART) | Combining lexical, semantic, and document signals from labeled examples |
| 4. RAG and synthesis | Ground generated answers in retrieved passages | Evidence selection, attribution, and limits of generation |
| 5. Domain signal extraction | Analyze financial documents such as SEC filings for domain-specific signals | Applying retrieval and feature design to specialized language |

Each layer builds on the one before it: the index produces candidates, evaluation tells us how well they rank, and later layers improve or interpret those candidates for richer tasks.

## Features at a glance

- A transparent BM25 retrieval foundation.
- BEIR-shaped data support for corpora, queries, and qrels (relevance judgments).
- Ranking metrics including $NDCG@10$ and Recall@k.
- A feature-based LTR reranking stage.
- Passage-grounded synthesis and financial signal extraction layers.
- A modular structure intended to make experiments easy to isolate and explain.

Continue with the [architecture deep dive](architecture.md) or jump to the [quickstart](quickstart.md).
