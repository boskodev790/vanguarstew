# Spec 040 — dual-order share summary

- **Status:** draft (SDD Phase 1 — Specify)
- **Owner:** benchmark
- **Issue:** #1093
- **Constitution:** [`AGENTS.md`](../../AGENTS.md) → *Benchmark integrity (M1–M3)*
- **Methodology:** [`blog/spec-driven-development.md`](../../blog/spec-driven-development.md)
- **Related:** [`benchmark/comparability.py`](../../benchmark/comparability.py) (artifact kind classification),
  [`benchmark/single_order_share.py`](../../benchmark/single_order_share.py) (single-order counterpart)

This spec makes the **existing, implicit** dual-order-share contract explicit. It describes the
as-built behavior of `benchmark/dual_order_share.py` (merged #917); it introduces **no behavior
change**. A judge whose verdicts were rarely produced under dual presentation is a weaker
robustness signal than the headline suggests — that coverage share must be written down and
verified.

## Why

`benchmark/judge.py` records per-outcome `judge_order_stats` (`agree`/`disagree`/`tie` are the
dual-presentation outcomes; `single`/`offline` are not). Nothing summarized how large a share of
the *categorized* outcomes were actually dual-order judged. `summarize_dual_order_share()` is the
reproducible read-only summary for CI dashboards; making its contract explicit lets reviewers check
dual-order-share changes against intent.

## User stories

1. **As a benchmark operator**, I can read `(agree + disagree + tie) / total` before trusting how
   dual-order-robust a run's judging was.
2. **As a CI maintainer**, I can log a stable `dual_order_share_headline()` string alongside the
   JSON summary.
3. **As a reviewer**, malformed-input handling, the generalization partition split, and every
   headline branch are written down.

## Acceptance criteria (EARS)

### Input coercion

- WHEN the replay `artifact` is not a `dict` THEN `summarize_dual_order_share(artifact)` SHALL treat
  it as `{}` and evaluate (not raise).
- `_dict(value)` SHALL return `value` when it is a `dict`, otherwise `{}`.

### Whole-number count semantics (`_is_int`)

- Only built-in `int` values SHALL count as whole-number counts.
- `bool` SHALL NOT be treated as an integer (avoids truthy counts).
- `float` values — including whole-number floats such as `5.0` — SHALL NOT be treated as integers.

### Finite numeric semantics (`_is_number`)

- Only finite, non-boolean `int`/`float` values SHALL count as numeric for headline share
  formatting.
- `bool`, `NaN`, `inf`, and non-numeric types SHALL NOT be treated as numeric.

### Order-stats extraction (`_order_stats`)

- `_order_stats(slice_)` SHALL return the slice's `judge_order_stats` mapping when it is a `dict`.
- WHEN the slice is not a `dict`, or `judge_order_stats` is missing or not a `dict`, THEN
  `_order_stats` SHALL return `{}`.

### Slice summary (`_slice_summary`)

- The categorized outcome keys SHALL be `agree`, `disagree`, `tie`, `single`, `offline`; the
  dual-presentation subset SHALL be `agree`, `disagree`, `tie`.
- WHEN every one of the five keys is present, an `int` (not `bool`), and `>= 0` THEN `total` SHALL
  be their sum and `dual_order_tasks` SHALL be `agree + disagree + tie`.
- WHEN any of the five counts is missing, non-`int`, `bool`, or negative THEN the slice SHALL
  return `{"total": None, "dual_order_tasks": None, "dual_order_share": None}`.
- WHEN the counts are coherent AND `total == 0` THEN the slice SHALL return
  `{"total": 0, "dual_order_tasks": 0, "dual_order_share": None}` (no share is defined over zero
  categorized outcomes, but the zero counts are reported).
- WHEN the counts are coherent AND `total > 0` THEN `dual_order_share` SHALL be
  `round(dual_order_tasks / total, 3)`.

### Artifact-kind branches (`summarize_dual_order_share`)

- Every returned summary SHALL include the keys `kind`, `total`, `dual_order_tasks`,
  `dual_order_share`, and `partitions`.
- WHEN `kind` is `single`, `multi`, or `invalid` THEN the summary SHALL carry the top-level slice
  summary and `partitions` SHALL be `None`.
- WHEN `kind` is `generalization` THEN the summary SHALL carry a `partitions` mapping with a
  `tuned` and a `held_out` slice summary, plus an overall `total`/`dual_order_tasks`/
  `dual_order_share`.
- WHEN `kind` is `generalization` AND both partitions report an `int` `total` and an `int`
  `dual_order_tasks` THEN the overall `total`/`dual_order_tasks` SHALL be their sums and the overall
  `dual_order_share` SHALL be `round(dual / total, 3)` when `total > 0`, else `None`.
- WHEN `kind` is `generalization` AND either partition's `total` or `dual_order_tasks` is not an
  `int` (a malformed partition) THEN the overall `total`/`dual_order_tasks`/`dual_order_share` SHALL
  all be `None`, while each partition's own summary is still reported.

### Dual-order share headline (`dual_order_share_headline`)

- WHEN the summary is not a `dict`, or `total` is not an `int`, or `total == 0` THEN the headline
  SHALL be exactly `"dual-order share: no judge stats available"`.
- WHEN `total` is a positive `int` THEN the headline SHALL be
  `"dual-order share: {share:.1%} ({dual}/{total} categorized task(s))"`, where `share` is the
  `dual_order_share` formatted as a percentage when numeric else `"n/a"`, and `dual` is
  `dual_order_tasks` when it is an `int` else `"n/a"`.

### Pure evaluation

- `summarize_dual_order_share` SHALL NOT mutate its input artifact.
- The module SHALL perform no I/O and SHALL never raise on malformed input (malformed counts yield
  `None` share fields instead).
