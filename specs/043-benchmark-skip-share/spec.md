# Spec 043 — skip share summary

- **Status:** draft (SDD Phase 1 — Specify)
- **Owner:** benchmark
- **Issue:** #1108
- **Constitution:** [`AGENTS.md`](../../AGENTS.md) → *Benchmark integrity (M1–M3)*
- **Methodology:** [`blog/spec-driven-development.md`](../../blog/spec-driven-development.md)
- **Related:** [`benchmark/comparability.py`](../../benchmark/comparability.py) (artifact kind classification),
  [`benchmark/skip_budget.py`](../../benchmark/skip_budget.py) (the pass/fail gate on the same counts)

This spec makes the **existing, implicit** skip-share contract explicit. It describes the as-built
behavior of `benchmark/skip_share.py`; it introduces **no behavior change**. A multi-repo headline
`composite_mean` can look healthy when only a fraction of the repos scored — that coverage signal
must be written down and verified.

## Why

A replay set has `repos` repositories but only `scored_repos` produce composite scores; the rest are
skipped. `skip_budget` *gates* whether too many were skipped, but a dashboard also needs a plain
read-only *report* of the skip share. `summarize_skip_share()` is that reproducible summary; making
its contract explicit lets reviewers check skip-share changes against intent.

## User stories

1. **As a benchmark operator**, I can read `(repos - scored_repos) / repos` before trusting a
   multi-repo or generalization headline mean.
2. **As a CI maintainer**, I can log a stable `skip_share_headline()` string alongside the JSON
   summary.
3. **As a reviewer**, malformed-accounting handling, the generalization partition split, and both
   headline branches are written down.

## Acceptance criteria (EARS)

### Input coercion

- WHEN the replay `artifact` is not a `dict` THEN `summarize_skip_share(artifact)` SHALL treat it as
  `{}` and evaluate (not raise).
- `_dict(value)` SHALL return `value` when it is a `dict`, otherwise `{}`.

### Whole-number count semantics (`_is_int`)

- Only built-in `int` values SHALL count as whole-number repo counts.
- `bool` SHALL NOT be treated as an integer (avoids truthy counts).
- `float` values — including whole-number floats such as `5.0` — SHALL NOT be treated as integers.

### Finite numeric semantics (`_is_number`)

- Only finite, non-boolean `int`/`float` values SHALL count as numeric for headline share
  formatting.
- `bool`, `NaN`, `inf`, and non-numeric types SHALL NOT be treated as numeric.

### Skip share (`_skip_share`)

- WHEN both `repos` and `scored` pass `_is_int` AND `repos > 0` AND `0 <= scored <= repos` THEN
  `_skip_share(repos, scored)` SHALL return `round((repos - scored) / repos, 3)` (a finite value in
  `[0.0, 1.0]`).
- WHEN `repos <= 0` THEN `_skip_share` SHALL return `None`.
- WHEN `scored < 0` THEN `_skip_share` SHALL return `None`.
- WHEN `scored > repos` THEN `_skip_share` SHALL return `None`.
- WHEN either argument fails `_is_int` (a `float`, `bool`, or non-number) THEN `_skip_share` SHALL
  return `None`.
- WHEN `scored == repos` and `repos > 0` THEN `_skip_share` SHALL return `0.0` (a coherent
  fully-scored set, distinct from `None` for incoherent counts).

### Slice summary (`_slice_summary`)

- SHALL read `repos` and `scored_repos` from the slice dict (missing keys treated as `None`).
- WHEN `_skip_share` returns a number THEN the slice SHALL return
  `{"repos": repos, "scored_repos": scored, "skipped": repos - scored, "skip_share": share}` with
  the original int counts.
- WHEN `_skip_share` returns `None` THEN `skipped` and `skip_share` SHALL be `None`, while `repos`
  and `scored_repos` SHALL still echo whichever count is a whole number (else `None`).

### Combined skip share (`_combined`)

- WHEN every partition slice has an `int` `repos` AND an `int` `scored_repos` THEN the combined
  slice SHALL sum `repos` and `scored_repos` across partitions and derive `skipped`/`skip_share`
  from those sums via `_skip_share`.
- WHEN any partition slice is missing an `int` `repos` or `scored_repos` THEN the combined slice
  SHALL be all `None` (`repos`, `scored_repos`, `skipped`, `skip_share`).

### Artifact-kind branches (`summarize_skip_share`)

- Every returned summary SHALL include the keys `kind`, `repos`, `scored_repos`, `skipped`,
  `skip_share`, and `partitions`.
- WHEN `kind` is `single`, `multi`, or `invalid` THEN the summary SHALL carry the top-level slice
  summary and `partitions` SHALL be `None`.
- WHEN `kind` is `generalization` THEN the summary SHALL carry a `partitions` mapping with a `tuned`
  and a `held_out` slice summary, plus the overall `_combined` result.
- WHEN `kind` is `generalization` AND a partition is malformed (missing counts) THEN the overall
  `skip_share` SHALL be `None`, while each partition's own summary is still reported.

### Skip share headline (`skip_share_headline`)

- WHEN `skipped` and `repos` are both `int` THEN the headline SHALL be
  `"skip share: {share_txt} ({skipped} of {repos} repos skipped)"`.
- WHEN `skipped` or `repos` is not an `int` THEN the headline SHALL drop the count clause and be
  `"skip share: {share_txt}"`.
- `share_txt` SHALL be the `skip_share` formatted as a percentage when numeric, else `"n/a"` (so a
  missing or non-finite share degrades instead of crashing the formatter).

### Pure evaluation

- `summarize_skip_share` SHALL NOT mutate its input artifact.
- The module SHALL perform no I/O and SHALL never raise on malformed input (malformed counts yield
  `None` fields instead).
