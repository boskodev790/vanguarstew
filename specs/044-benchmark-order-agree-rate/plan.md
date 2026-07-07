# Plan 044 — order agree rate summary

- **Status:** draft (SDD Phase 2 — Plan)
- **Spec:** [`spec.md`](./spec.md) · **Issue:** #1112

Maps the [spec](./spec.md) onto `benchmark/order_agree_rate.py` as-built. No product code.

## EARS → test mapping

| Spec section | Test group in `test_spec_044_order_agree_rate.py` |
| ------------ | -------------------------------------------------- |
| Input coercion | `test_non_dict_artifact_coerced_to_empty_dict`, `test_dict_helper_returns_dict_or_empty` |
| Whole-number count semantics | `test_is_int_rejects_bool`, `test_is_int_rejects_float_whole_numbers` |
| Finite numeric semantics | `test_bool_and_non_finite_not_numeric` |
| Order-stats extraction | `test_order_stats_returns_dict_or_empty`, `test_order_stats_warns_on_non_dict` |
| Slice summary | `test_slice_summary_happy_path`, `test_slice_summary_zero_total_reports_zero_counts`, `test_slice_summary_missing_key_withholds`, `test_slice_summary_negative_or_non_int_withholds` |
| Combined agree rate | `test_combined_sums_coherent_partitions`, `test_combined_withholds_when_any_partition_incoherent` |
| Artifact-kind branches | `test_single_and_multi_kinds`, `test_invalid_kind_returns_none_fields`, `test_summary_always_includes_required_keys`, `test_generalization_partitions_and_overall`, `test_generalization_partial_partition_withholds_overall` |
| Order agree rate headline | `test_headline_single_exact_format`, `test_headline_generalization_appends_partition_rates`, `test_headline_zero_total_shows_unavailable`, `test_headline_non_dict_summary_coerced` |
| Pure evaluation | `test_summarize_does_not_mutate_artifact` |

## Verification strategy

One contract-test group per EARS section; integration and headline-format tests live alongside in
`tests/test_order_agree_rate.py`. The contract tests assert the as-built module already satisfies
every criterion — a failure marks a spec/behavior drift, not a feature request.
