# Spec 044 — order agree rate summary

- **Status:** draft (SDD Phase 1 — Specify)
- **Owner:** benchmark
- **Issue:** #1112
- **Constitution:** [`AGENTS.md`](../../AGENTS.md) → *Benchmark integrity (M1–M3)*
- **Methodology:** [`blog/spec-driven-development.md`](../../blog/spec-driven-development.md)
- **Related:** [`benchmark/comparability.py`](../../benchmark/comparability.py) (artifact kind classification),
  [`benchmark/disagreement_outlook.py`](../../benchmark/disagreement_outlook.py) (disagreement counterpart)

This spec makes the **existing, implicit** order-agree-rate contract explicit. It describes the
as-built behavior of `benchmark/order_agree_rate.py`; it introduces **no behavior change**.
`disagreement_outlook` reports the `disagreement_rate`; this utility normalizes the underlying
`judge_order_stats` agree/disagree/tie counts into an *agree* rate that must be written down and
verified.

## Why

`benchmark/judge.py` records dual-order outcomes as `agree`/`disagree`/`tie` counts under
`judge_order_stats`, but nothing reported the plain agree rate `agree / (agree + disagree + tie)`.
`summarize_order_agree_rate()` is the reproducible read-only summary for CI dashboards; making its
contract explicit lets reviewers check order-agree-rate changes against intent.

## User stories

1. **As a benchmark operator**, I can read the dual-order agree rate before trusting how stable a
   run's judging was.
2. **As a CI maintainer**, I can log a stable `order_agree_rate_headline()` string alongside the
   JSON summary.
3. **As a reviewer**, malformed-stats handling, the generalization partition split, and both
   headline forms are written down.

## Acceptance criteria (EARS)

### Input coercion

- WHEN the replay `artifact` is not a `dict` THEN `summarize_order_agree_rate(artifact)` SHALL treat
  it as `{}` and evaluate (not raise).
- `_dict(value)` SHALL return `value` when it is a `dict`, otherwise `{}`.

### Whole-number count semantics (`_is_int`)

- Only built-in `int` values SHALL count as whole-number counts.
- `bool` SHALL NOT be treated as an integer (avoids truthy counts).
- `float` values — including whole-number floats such as `5.0` — SHALL NOT be treated as integers.

### Finite numeric semantics (`_is_number`)

- Only finite, non-boolean `int`/`float` values SHALL count as numeric for headline rate
  formatting.
- `bool`, `NaN`, `inf`, and non-numeric types SHALL NOT be treated as numeric.

### Order-stats extraction (`_order_stats`)

- `_order_stats(slice_)` SHALL return the slice's `judge_order_stats` mapping when it is a `dict`.
- WHEN `judge_order_stats` is present but not a `dict` THEN `_order_stats` SHALL log a warning and
  return `{}`; a missing value SHALL return `{}` silently.

### Slice summary (`_slice_summary`)

- The dual-order outcome keys SHALL be `agree`, `disagree`, `tie`.
- WHEN all three keys are present, an `int` (not `bool`), and `>= 0` THEN `total` SHALL be their sum
  and `agree_rate` SHALL be `round(agree / total, 3)` when `total > 0`.
- WHEN any of the three counts is missing, non-`int`, `bool`, or negative THEN the slice SHALL
  return `agree`/`disagree`/`tie`/`total`/`agree_rate` all `None`.
- WHEN the counts are coherent AND `total == 0` THEN the slice SHALL return the zero counts with
  `agree_rate` `None` (no rate is defined over zero dual-order outcomes).

### Combined agree rate (`_combined`)

- WHEN both partition slices carry `int` `agree`/`disagree`/`tie`/`total` THEN the combined slice
  SHALL sum each count across partitions and derive `agree_rate` from the summed totals
  (`None` when the summed `total` is 0).
- WHEN either partition slice is missing any `int` count THEN the combined slice SHALL be all
  `None`.

### Artifact-kind branches (`summarize_order_agree_rate`)

- Every returned summary SHALL include the keys `kind`, `agree`, `disagree`, `tie`, `total`,
  `agree_rate`, and `partitions`.
- WHEN `kind` is `single`, `multi`, or `invalid` THEN the summary SHALL carry the top-level slice
  summary and `partitions` SHALL be `None`.
- WHEN `kind` is `generalization` THEN the summary SHALL carry a `partitions` mapping with a `tuned`
  and a `held_out` slice summary, plus the overall `_combined` result.
- WHEN `kind` is `generalization` AND a partition is malformed (missing stats) THEN the overall
  `agree_rate` SHALL be `None`, while each partition's own summary is still reported.

### Order agree rate headline (`order_agree_rate_headline`)

- WHEN the summary is not a `dict`, or `total` is not an `int`, or `total == 0` THEN the headline
  SHALL be exactly `"order agree rate: no dual-order stats available"`.
- WHEN `total` is a positive `int` AND `kind` is not `generalization` THEN the headline SHALL be
  `"order agree rate: {rate} ({agree}/{total})"`, where `{rate}` is the `agree_rate` formatted as a
  percentage when numeric else `"n/a"`.
- WHEN `total` is a positive `int` AND `kind` is `generalization` THEN the headline SHALL append the
  per-partition rates: `"order agree rate: {rate} ({agree}/{total}) [tuned {t}, held-out {h}]"`.

### Pure evaluation

- `summarize_order_agree_rate` SHALL NOT mutate its input artifact.
- The module SHALL perform no I/O and SHALL never raise on malformed input (malformed counts yield
  `None` fields instead).
