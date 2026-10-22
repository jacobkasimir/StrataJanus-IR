# Agent guidance

StrataJanus-IR is a from-scratch Python search engine built in four strata: lexical indexing and BM25, dense and hybrid retrieval, learned ranking, and RAG. Each stratum is evaluated for retrieval quality and cost.

## Layout

- `src/stratajanus/` — installable search engine package.
- `scripts/` — dataset download and evaluation command placeholders.
- `benchmarks/` — comparisons with reference implementations.
- `tests/` — unit and property-based tests.
- `configs/` — experiment configuration files.
- `data/` — downloaded raw and processed datasets.
- `indexes/` — generated indexes.
- `results/` — tracked JSON experiment outputs.
- `docs/` — design, evaluation, dataset notes, and ADRs.
- `.github/` — CI and contribution templates.

## Commands

- `make install`
- `make lint`
- `make test`
- `make bench`

## Conventions

Use type hints on all public functions, add docstrings, keep code Ruff-clean, and add tests for every new module. Use deterministic seeds and avoid network calls in unit tests.

## Evaluation rules

Never hand-type result numbers; generate results from files in `results/`. Report confidence intervals for every comparison. Prevent train/test leakage.

## Do not

Never commit datasets, indexes, model weights, or secrets. Keep heavy dependencies out of the core. Do not use Elasticsearch or Lucene in core code.
