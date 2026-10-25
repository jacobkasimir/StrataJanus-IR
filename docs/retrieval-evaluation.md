# SciFact retrieval evaluation

`scripts/evaluate_scifact.py` evaluates BM25 rankings against the query and
relevance-judgment files produced by the SciFact preparation workflow. It
evaluates every query in the chosen split, retrieves up to 100 documents per
query, and writes aggregate and per-query results as JSON.

## Data and query splits

The evaluator reads query text from `data/processed/scifact/queries.jsonl`
and relevance judgments from `data/processed/scifact/qrels/`. SciFact's
training qrels contain 809 queries; the official held-out test qrels contain
300 different queries.

Development and validation IDs were derived only from the training qrels by
`scripts/create_scifact_validation_split.py`. The script sorts the training
query IDs, shuffles them with `random.Random(42)`, assigns the first
`int(809 * 0.2) = 161` IDs to validation, and saves the remaining 648 as
development-training IDs. Both ID lists are sorted before being written to
`configs/scifact_eval_split.json`, together with the seed, fraction, and
training-qrels SHA-256 fingerprint. The evaluator selects only the saved
validation IDs from `train.tsv`; it verifies that the split fingerprint still
matches the training qrels.

The official `test.tsv` judgments form a separate held-out assessment. Test
evaluation requires the explicit `--allow-test` option. Use validation for
parameter selection; do not use held-out test results to choose parameters.

## Run an evaluation

After preparing SciFact and building the chosen saved index, run validation
with a new output path. The script refuses to overwrite an existing report.

```bash
PYTHONPATH=src python scripts/evaluate_scifact.py \
  --split validation \
  --format fixed32 \
  --k1 1.2 \
  --b 0.75 \
  --output reports/evaluation/my-validation-run.json
```

`--split` accepts `validation` or `test`; `--format` accepts `json`,
`fixed32`, or `vb`. For an intentional held-out assessment, use
`--split test --allow-test` and record the already chosen configuration. The
script records the split, index format, BM25 parameters, input fingerprints,
aggregate means, and per-query metrics, judged-relevant count, and ranked
document IDs in each report.

## Metric conventions

Each metric is computed per query and the reported aggregate is the arithmetic
mean over queries:

- **nDCG@10:** graded gain is `2^relevance - 1`, discounted at one-based rank
  `r` by `log2(r + 1)`, and normalized by the ideal ordering of the judged
  relevance grades at cutoff 10.
- **Recall@100:** the number of judged-relevant documents (relevance greater
  than zero) retrieved in the first 100, divided by the total number of
  judged-relevant documents for that query.
- **MRR@10:** the reciprocal rank of the first judged-relevant document in
  the first 10 results, or zero if none appears there.

Documents absent from the qrels receive zero gain for nDCG scoring. That is an
evaluation convention: an unjudged document is not thereby proven irrelevant.
Recall and MRR count only documents with positive relevance judgments. Queries
without any positive judgment are rejected.

## Independent metric audit

The metric implementation was cross-checked with the installed
`pytrec_eval-terrier` 0.5.11 package (`pytrec_eval`). Its supported measures
include `ndcg_cut`, `recall`, and `recip_rank`; it does not expose a bounded
`MRR@10` measure. The audit uses `ndcg_cut.10` and `recall.100` directly, and
reproduces MRR@10 by passing only the first ten ranked documents to
`recip_rank`. Synthetic checks verify that a relevant document at rank 11
therefore gives MRR@10 zero. Scores are generated as strictly descending
rank-based values, preserving the saved ordering without display-rounded BM25
scores.

There is a convention difference for graded nDCG: this package's
`ndcg_cut.10` uses raw relevance as gain, while StrataJanus-IR uses
`2^relevance - 1`. A reversed grade-2/grade-1 synthetic ranking detects the
difference (0.859719 versus 0.796708). Thus the measures are not generally
equivalent for graded qrels. SciFact's audited validation qrels use binary
positive labels, for which both gain functions coincide. Recall uses a
positive relevance threshold and the total count of positive qrels as its
denominator in both implementations. Unjudged retrieved documents receive
zero gain / are not relevant. The audit explicitly supplies empty query runs
so they remain in the macro average; the library returns zero metrics for
these queries. StrataJanus-IR rejects queries with no positive judgments;
pytrec_eval instead returns zero metrics for an explicit nonempty run against
all-zero qrels (and an empty measure mapping if that run is empty). Duplicate
ranked IDs are rejected by StrataJanus-IR; a score mapping cannot represent
duplicate document IDs, so that rejection is tested separately.

The synthetic checks cover perfect and reversed graded rankings, unjudged
documents above relevant ones, ranks 10, 11, 100, and 101, multiple relevant
documents, empty runs, and macro averaging. Run them with:

```bash
PYTHONPATH=src python -m pytest tests/test_metric_crosscheck.py tests/test_retrieval_metrics.py -v
```

The reproducible saved-report audit reads the ranking from the report, checks
the qrels SHA-256 fingerprint, and never reruns BM25 or writes to the report:

```bash
PYTHONPATH=src python scripts/audit_scifact_metrics.py \
  reports/evaluation/scifact-bm25-validation.json
```

On the saved validation report, the audit compared all 161 per-query rankings
against the matching canonical training qrels. Per-query values and macro
means agreed with the report for nDCG@10, Recall@100, and MRR@10; the maximum
absolute difference was 0 for each metric. SciFact's audited relevance labels
are binary. The saved final-test report was left untouched and was not audited
in this cross-check.

## Recorded results

The default-parameter validation report is
`reports/evaluation/scifact-bm25-validation.json` (161 queries, `fixed32`,
`k1=1.2`, `b=0.75`): nDCG@10 **0.709623**, Recall@100 **0.913043**, and
MRR@10 **0.680060**. Its per-query results include the top-100 document IDs.

The validation split was also used for the recorded nine-point BM25 parameter
grid. The frozen plan, aggregate table, retained run reports, and paired
bootstrap comparison against the default are in
`reports/evaluation/tuning/experiment-plan.md` and
`reports/evaluation/tuning/results.md`. The grid winner's nDCG@10 difference
from the default was +0.001810; its paired 95% bootstrap interval was
[-0.007122, +0.011445]. The interval includes zero, so the validation data
did not provide convincing evidence to change the defaults. The comparison is
exploratory because the grid winner was selected on the same validation set.

The final held-out report,
`reports/evaluation/scifact-bm25-final-test.json`, records the retained
defaults (`k1=1.2`, `b=0.75`) on 300 test queries: nDCG@10 **0.661676**,
Recall@100 **0.885889**, and MRR@10 **0.627618**. These metrics are an
assessment of the recorded configuration; they were not used to choose new
parameters.

## Reading failure examples

For the default-parameter validation report, query `1096` has one
judged-relevant document, retrieved at rank 94. It counts for Recall@100 but
not nDCG@10 or MRR@10. For query `1008`, its single judged-relevant document
does not appear in the top 100. The query contains `RUNX`, which does not
appear in that judged document's title or text; this lexical mismatch may
contribute to the miss. Such examples show outcomes under this lexical ranker,
not that unjudged documents are irrelevant or that any one cause is proven.

BM25 uses `k1` and `b` while scoring each query, so changing them does not
require rebuilding the index. If tuning, choose parameters using validation
queries, record the selection rule before comparing results, and reserve the
official test qrels for the final held-out assessment.
