"""Contract tests for specs/043-benchmark-skip-share — assert skip_share.py satisfies the
spec's EARS criteria: count parsing, skip fraction, slice/combined summaries, artifact-kind
branches (including the generalization partition split), headline branches, and pure
evaluation. Offline, deterministic.
"""

import copy
import math
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from benchmark.skip_share import (  # noqa: E402
    _combined,
    _dict,
    _is_int,
    _is_number,
    _skip_share,
    _slice_summary,
    skip_share_headline,
    summarize_skip_share,
)

_REQUIRED_KEYS = frozenset({"kind", "repos", "scored_repos", "skipped", "skip_share", "partitions"})


# --- Input coercion -------------------------------------------------------------------------


@pytest.mark.parametrize("bad", (None, "not a dict", 42, [1, 2], ()))
def test_non_dict_artifact_coerced_to_empty_dict(bad):
    out = summarize_skip_share(bad)
    assert out["kind"] == "invalid"
    assert out["skip_share"] is None
    assert out["partitions"] is None


def test_dict_helper_returns_dict_or_empty():
    d = {"a": 1}
    assert _dict(d) is d
    for bad in (None, "x", 3, [1], ()):
        assert _dict(bad) == {}


# --- Whole-number count semantics (_is_int) -------------------------------------------------


def test_is_int_rejects_bool():
    assert _is_int(0) and _is_int(7)
    assert not _is_int(True) and not _is_int(False)


def test_is_int_rejects_float_whole_numbers():
    assert not _is_int(5.0)
    assert not _is_int("5")
    assert not _is_int(None)


# --- Finite numeric semantics (_is_number) --------------------------------------------------


def test_bool_and_non_finite_not_numeric():
    assert _is_number(0.2) and _is_number(3)
    assert not _is_number(True)
    assert not _is_number(math.nan)
    assert not _is_number(math.inf)
    assert not _is_number("0.5")


# --- Skip share (_skip_share) ---------------------------------------------------------------


def test_skip_share_valid_rates():
    assert _skip_share(5, 4) == 0.2
    assert _skip_share(4, 0) == 1.0


def test_skip_share_fully_scored_is_zero():
    assert _skip_share(4, 4) == 0.0     # coherent, fully scored -> 0.0, not None


def test_skip_share_zero_repos():
    assert _skip_share(0, 0) is None
    assert _skip_share(-1, 0) is None


def test_skip_share_negative_scored():
    assert _skip_share(5, -1) is None


def test_skip_share_scored_exceeds_repos():
    assert _skip_share(3, 5) is None


def test_skip_share_non_integer_counts():
    assert _skip_share(5.0, 4) is None
    assert _skip_share(5, True) is None
    assert _skip_share(None, None) is None


# --- Slice summary (_slice_summary) ---------------------------------------------------------


def test_slice_summary_happy_path():
    assert _slice_summary({"repos": 5, "scored_repos": 4}) == {
        "repos": 5, "scored_repos": 4, "skipped": 1, "skip_share": 0.2,
    }


def test_slice_summary_incoherent_echoes_raw_ints():
    # scored > repos is incoherent: skipped/skip_share are None, but the raw int counts echo back.
    out = _slice_summary({"repos": 3, "scored_repos": 5})
    assert out == {"repos": 3, "scored_repos": 5, "skipped": None, "skip_share": None}


def test_slice_summary_non_int_counts_become_none():
    out = _slice_summary({"repos": 5.0, "scored_repos": 4})
    assert out == {"repos": None, "scored_repos": 4, "skipped": None, "skip_share": None}


# --- Combined skip share (_combined) --------------------------------------------------------


def test_combined_sums_coherent_partitions():
    tuned = {"repos": 4, "scored_repos": 4, "skipped": 0, "skip_share": 0.0}
    held = {"repos": 4, "scored_repos": 2, "skipped": 2, "skip_share": 0.5}
    assert _combined(tuned, held) == {
        "repos": 8, "scored_repos": 6, "skipped": 2, "skip_share": 0.25,
    }


def test_combined_withholds_when_any_partition_incoherent():
    tuned = {"repos": 4, "scored_repos": 4, "skipped": 0, "skip_share": 0.0}
    bad = {"repos": None, "scored_repos": None, "skipped": None, "skip_share": None}
    assert _combined(tuned, bad) == {
        "repos": None, "scored_repos": None, "skipped": None, "skip_share": None,
    }


# --- Artifact-kind branches (summarize_skip_share) ------------------------------------------


def test_single_and_multi_kinds():
    single = summarize_skip_share({"repos": 5, "scored_repos": 4})
    assert single["kind"] == "single"
    assert single["skip_share"] == 0.2 and single["skipped"] == 1
    assert single["partitions"] is None

    multi = summarize_skip_share({"per_repo": [{}, {}], "repos": 10, "scored_repos": 8})
    assert multi["kind"] == "multi" and multi["partitions"] is None
    assert multi["skip_share"] == 0.2


def test_invalid_kind_returns_none_fields():
    out = summarize_skip_share({})
    assert out["kind"] == "invalid"
    assert out["skip_share"] is None and out["skipped"] is None
    assert out["partitions"] is None


def test_summary_always_includes_required_keys():
    for art in ({}, {"repos": 5, "scored_repos": 4}, {"per_repo": [{}], "repos": 2, "scored_repos": 1},
                {"generalization_gap": 0.05, "tuned": {"repos": 4, "scored_repos": 4},
                 "held_out": {"repos": 4, "scored_repos": 2}}):
        assert _REQUIRED_KEYS <= set(summarize_skip_share(art))


def test_generalization_partitions_and_overall():
    art = {
        "generalization_gap": 0.05,
        "tuned": {"repos": 4, "scored_repos": 4},     # skip 0.0
        "held_out": {"repos": 4, "scored_repos": 2},  # skip 0.5
    }
    out = summarize_skip_share(art)
    assert out["kind"] == "generalization"
    assert out["repos"] == 8 and out["scored_repos"] == 6      # summed across partitions
    assert out["skipped"] == 2 and out["skip_share"] == 0.25
    assert out["partitions"]["tuned"]["skip_share"] == 0.0
    assert out["partitions"]["held_out"]["skip_share"] == 0.5


def test_generalization_partial_partition_withholds_overall():
    # held_out missing scored_repos -> overall withholds, but each partition is still reported.
    art = {
        "generalization_gap": 0.0,
        "tuned": {"repos": 4, "scored_repos": 4},
        "held_out": {"repos": 4},
    }
    out = summarize_skip_share(art)
    assert out["skip_share"] is None and out["repos"] is None
    assert out["partitions"]["tuned"]["skip_share"] == 0.0
    assert out["partitions"]["held_out"]["skip_share"] is None
    assert out["partitions"]["held_out"]["repos"] == 4


# --- Skip share headline (skip_share_headline) ----------------------------------------------


def test_headline_with_counts_exact_format():
    summary = summarize_skip_share({"repos": 5, "scored_repos": 4})
    assert skip_share_headline(summary) == "skip share: 20.0% (1 of 5 repos skipped)"


def test_headline_zero_share_exact_format():
    summary = summarize_skip_share({"repos": 4, "scored_repos": 4})
    assert skip_share_headline(summary) == "skip share: 0.0% (0 of 4 repos skipped)"


def test_headline_no_counts_clause():
    # a finite share with no whole-number skipped/repos drops the "(x of y)" clause.
    assert skip_share_headline({"skip_share": 0.2}) == "skip share: 20.0%"
    assert skip_share_headline({"skip_share": 0.2, "skipped": 1, "repos": None}) == "skip share: 20.0%"


def test_headline_nan_share_shows_na():
    assert skip_share_headline({"skip_share": float("nan"), "skipped": 1, "repos": 5}).startswith(
        "skip share: n/a")
    assert skip_share_headline({"skip_share": None}) == "skip share: n/a"


def test_headline_non_dict_summary_coerced():
    assert skip_share_headline("not a dict") == "skip share: n/a"


# --- Pure evaluation ------------------------------------------------------------------------


def test_summarize_does_not_mutate_artifact():
    art = {
        "generalization_gap": 0.05,
        "tuned": {"repos": 4, "scored_repos": 4},
        "held_out": {"repos": 4, "scored_repos": 2},
    }
    snapshot = copy.deepcopy(art)
    summarize_skip_share(art)
    assert art == snapshot
