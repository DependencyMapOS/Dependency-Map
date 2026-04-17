# Reviewer Metric

This document defines how contributors should review GraphCodeBERT ranking changes and how to summarize that review into a simple metric.

## Evaluation checklist (Phase 0 loop)

Use this sequence after [docs/MODEL_SETUP.md](MODEL_SETUP.md) environment setup:

1. **Compare rankers** on a fixed `base` / `head` (same SHAs you care about for a PR or experiment):

   `cd backend && uv run python -m cpg_builder.main compare-rankers --repo .. --out-dir ../artifacts/ranker-compare --base <ref> --head <ref>`

2. **Generate the labeling JSONL** (starter rows for human review):

   `uv run python -m cpg_builder.main label-ranker-results --compare-dir ../artifacts/ranker-compare --out ../artifacts/ranker-compare/ranker-labels.jsonl`

3. **Review and set `review_label`** on each row (see [Required Review Labels](#required-review-labels)). Aim for a first batch of at least **30–50** judged rows before trusting aggregate metrics.

4. **Aggregate metrics**:

   `uv run python scripts/aggregate_ranker_labels.py ../artifacts/ranker-compare/ranker-labels.jsonl`

5. **Optional dataset prep** (after labels look sane):

   `uv run python -m cpg_builder.main prepare-graphcodebert-dataset --labels ../artifacts/ranker-compare/ranker-labels.jsonl --out-dir ../artifacts/graphcodebert-dataset`

6. **Optional smoke fine-tune** (validates the training path):

   `uv run python scripts/train_graphcodebert.py --train ../artifacts/graphcodebert-dataset/graphcodebert-train.jsonl --val ../artifacts/graphcodebert-dataset/graphcodebert-val.jsonl --out-dir ../artifacts/graphcodebert-model`

For a one-liner **compare, label file generation, and aggregation** (metrics reflect whatever `review_label` is set to—edit the JSONL after for real review), use `npm run ranker:eval` from the repository root (see root [README.md](../README.md)).

## Purpose

The goal is to answer one question:

> Did GraphCodeBERT improve the ordering of findings compared with the heuristic ranker?

This review is about ranking quality, not whether the whole pipeline ran successfully.

## Primary Review File

Review:

- `artifacts/ranker-compare/ranker-labels.jsonl`

Supporting context:

- `artifacts/ranker-compare/ranker-comparison.json`
- `artifacts/ranker-compare/heuristic/verifier_audit.json`
- `artifacts/ranker-compare/graphcodebert/verifier_audit.json`

## Required Review Labels

Each row in `ranker-labels.jsonl` should end with one of:

- `better`
- `expected_better`
- `worse`
- `noisy_promotion`
- `unclear`

## Label Meaning

### `better`

Use `better` when GraphCodeBERT improved ranking quality.

Examples:

- a `confirmed` or `partially_confirmed` finding was promoted upward
- an `unconfirmed` or noisy finding was pushed lower
- a more important seam moved earlier in the list

### `worse`

Use `worse` when GraphCodeBERT made ranking quality worse.

Examples:

- a strong `confirmed` finding was demoted
- a weak or noisy finding was promoted ahead of stronger findings
- a low-value seam displaced a more actionable finding

### `unclear`

Use `unclear` when you cannot confidently say whether the move helped.

Examples:

- the finding remains `unconfirmed`
- stitcher coverage is low and certainty is reduced
- the candidate looks plausible but the ranking significance is ambiguous

### `expected_better`

Use `expected_better` when the model improved ranking, but the improvement is obvious rather than especially insightful.

Examples:

- a high-confidence confirmed schema finding moved upward
- the movement reinforces a strong signal that heuristics already should have favored

### `noisy_promotion`

Use `noisy_promotion` when the model promoted a low-quality or unconfirmed signal.

Examples:

- an unconfirmed Celery task finding was pushed much higher
- a noisy seam moved up without strong verifier support

## Review Priority

Review in this order:

1. `top_promotions` with `confirmed` or `partially_confirmed` outcomes
2. `top_drops` with `confirmed` or `partially_confirmed` outcomes
3. `unclear` rows
4. low-confidence worker and frontend route-binding rows

## What To Check In Each Row

Look at:

- `bucket`
- `heuristic_rank`
- `graphcodebert_rank`
- `rank_delta`
- `heuristic_outcome`
- `graphcodebert_outcome`
- `heuristic_candidate`
- `graphcodebert_candidate`
- `review_notes`

Ask:

- Did a more important finding move up?
- Did a less useful finding move down?
- Did a verified finding lose priority?
- Is the move explainable based on seam importance?

## Significance Of The Review

These labels are used for:

- deciding whether GraphCodeBERT is helping enough to keep in the loop
- determining whether the current blended ranker is good enough for contributor use
- building the first fine-tuning dataset for GraphCodeBERT

This means the review labels are not cosmetic. They are the first quality signal for future model training.

## Simple Reviewer Metric

Use this metric on the reviewed file:

### Net Ranking Improvement

```text
net_improvement = better_count - worse_count
```

Interpretation:

- positive: GraphCodeBERT helped more often than it hurt
- zero: GraphCodeBERT is neutral
- negative: GraphCodeBERT is currently making the list worse

### Review Precision

```text
review_precision = better_count / (better_count + worse_count)
```

Ignore `unclear` rows for this metric.

Interpretation:

- `>= 0.70`: promising
- `0.50 - 0.69`: mixed, needs more review or tuning
- `< 0.50`: current ranking is not improving enough

### Unclear Rate

```text
unclear_rate = unclear_count / total_reviewed
```

Interpretation:

- low: reviewers can judge ranking quality clearly
- high: the dataset is too ambiguous and needs better stitcher coverage, clearer invariants, or more focused review slices

## Recommended Decision Rule

Use this simple rule for the current phase:

- continue with GraphCodeBERT ranking if `review_precision >= 0.70` and `net_improvement > 0`
- keep collecting labels if `review_precision` is mixed but not clearly negative
- do not fine-tune yet if `unclear_rate` is still high

## Reviewer Guidance For This Repo

The most important finding families in this repo are:

- `schema_entity_still_referenced`
- `missing_guard_or_rls_gap`
- `frontend_route_binding`
- `celery_task_binding`

In practice:

- promoted `confirmed` schema findings are often strong positives
- demoted `confirmed` schema findings are often strong negatives
- `frontend_route_binding` rows are harder to trust when stitcher coverage is low
- `celery_task_binding` rows often need closer manual review because they are more likely to stay `unconfirmed`

## Current Team Workflow

1. Run `compare-rankers`
2. Run `label-ranker-results`
3. Review and correct `review_label`
4. Summarize `better`, `worse`, and `unclear`
5. Decide whether the ranking quality is improving enough
6. Use reviewed labels as future GraphCodeBERT fine-tuning data
