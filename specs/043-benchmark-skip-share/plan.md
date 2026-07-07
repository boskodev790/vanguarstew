# Plan 043 — skip share summary

- **Status:** draft (SDD Phase 2 — Plan)
- **Spec:** [`spec.md`](./spec.md) · **Issue:** #1108

Maps the [spec](./spec.md) onto `benchmark/skip_share.py` as-built. No product code.

## EARS → test mapping

| Spec section | Test group in `test_spec_043_skip_share.py` |
| ------------ | ------------------------------------------- |
| Input coercion | `test_non_dict_artifact_coerced_to_empty_dict`, `test_dict_helper_returns_dict_or_empty` |
| Whole-number count semantics | `test_is_int_rejects_bool`, `test_is_int_rejects_float_whole_numbers` |
| Finite numeric semantics | `test_bool_and_non_finite_not_numeric` |
| Skip share | `test_skip_share_valid_rates`, `test_skip_share_fully_scored_is_zero`, `test_skip_share_zero_repos`, `test_skip_share_negative_scored`, `test_skip_share_scored_exceeds_repos`, `test_skip_share_non_integer_counts` |
| Slice summary | `test_slice_summary_happy_path`, `test_slice_summary_incoherent_echoes_raw_ints`, `test_slice_summary_non_int_counts_become_none` |
| Combined skip share | `test_combined_sums_coherent_partitions`, `test_combined_withholds_when_any_partition_incoherent` |
| Artifact-kind branches | `test_single_and_multi_kinds`, `test_invalid_kind_returns_none_fields`, `test_summary_always_includes_required_keys`, `test_generalization_partitions_and_overall`, `test_generalization_partial_partition_withholds_overall` |
| Skip share headline | `test_headline_with_counts_exact_format`, `test_headline_zero_share_exact_format`, `test_headline_no_counts_clause`, `test_headline_nan_share_shows_na`, `test_headline_non_dict_summary_coerced` |
| Pure evaluation | `test_summarize_does_not_mutate_artifact` |

## Verification strategy

One contract-test group per EARS section; integration and CLI tests stay in
`tests/test_skip_share.py`. The contract tests assert the as-built module already satisfies every
criterion — a failure marks a spec/behavior drift, not a feature request.
