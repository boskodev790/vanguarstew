"""Contract tests for specs/044-benchmark-order-agree-rate — assert order_agree_rate.py
satisfies the spec's EARS criteria: count parsing, slice/combined summaries, artifact-kind
branches (including the generalization partition split), both headline forms, and pure
evaluation. Offline, deterministic.
"""

import copy
import logging
import math
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from benchmark.order_agree_rate import (  # noqa: E402
    _combined,
    _dict,
    _is_int,
    _is_number,
    _order_stats,
    _slice_summary,
    order_agree_rate_headline,
    summarize_order_agree_rate,
)

_REQUIRED_KEYS = frozenset({"kind", "agree", "disagree", "tie", "total", "agree_rate", "partitions"})


def _stats(agree=0, disagree=0, tie=0):
    return {"judge_order_stats": {"agree": agree, "disagree": disagree, "tie": tie}}


# --- Input coercion -------------------------------------------------------------------------


@pytest.mark.parametrize("bad", (None, "not a dict", 42, [1, 2], ()))
def test_non_dict_artifact_coerced_to_empty_dict(bad):
    out = summarize_order_agree_rate(bad)
    assert out["kind"] == "invalid"
    assert out["total"] is None and out["agree_rate"] is None
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
    assert _is_number(0.6) and _is_number(3)
    assert not _is_number(True)
    assert not _is_number(math.nan)
    assert not _is_number(math.inf)
    assert not _is_number("0.5")


# --- Order-stats extraction (_order_stats) --------------------------------------------------


def test_order_stats_returns_dict_or_empty():
    stats = {"agree": 1}
    assert _order_stats({"judge_order_stats": stats}) is stats
    assert _order_stats({}) == {}
    assert _order_stats(None) == {}


def test_order_stats_warns_on_non_dict(caplog):
    with caplog.at_level(logging.WARNING, logger="benchmark.order_agree_rate"):
        assert _order_stats({"judge_order_stats": "nope"}) == {}
    assert any("judge_order_stats is str" in r.message for r in caplog.records)


# --- Slice summary (_slice_summary) ---------------------------------------------------------


def test_slice_summary_happy_path():
    out = _slice_summary(_stats(agree=6, disagree=2, tie=2))
    assert out == {"agree": 6, "disagree": 2, "tie": 2, "total": 10, "agree_rate": 0.6}


def test_slice_summary_zero_total_reports_zero_counts():
    out = _slice_summary(_stats())
    assert out == {"agree": 0, "disagree": 0, "tie": 0, "total": 0, "agree_rate": None}


def test_slice_summary_missing_key_withholds():
    out = _slice_summary({"judge_order_stats": {"agree": 1}})
    assert out == {"agree": None, "disagree": None, "tie": None, "total": None, "agree_rate": None}


@pytest.mark.parametrize("stats", [
    {"agree": -1, "disagree": 0, "tie": 0},   # negative
    {"agree": 1.0, "disagree": 0, "tie": 0},  # float
    {"agree": True, "disagree": 0, "tie": 0},  # bool
])
def test_slice_summary_negative_or_non_int_withholds(stats):
    out = _slice_summary({"judge_order_stats": stats})
    assert out["total"] is None and out["agree_rate"] is None


# --- Combined agree rate (_combined) --------------------------------------------------------


def test_combined_sums_coherent_partitions():
    tuned = {"agree": 3, "disagree": 1, "tie": 0, "total": 4, "agree_rate": 0.75}
    held = {"agree": 2, "disagree": 1, "tie": 1, "total": 4, "agree_rate": 0.5}
    out = _combined(tuned, held)
    assert out == {"agree": 5, "disagree": 2, "tie": 1, "total": 8, "agree_rate": 0.625}


def test_combined_withholds_when_any_partition_incoherent():
    tuned = {"agree": 3, "disagree": 1, "tie": 0, "total": 4, "agree_rate": 0.75}
    bad = {"agree": None, "disagree": None, "tie": None, "total": None, "agree_rate": None}
    out = _combined(tuned, bad)
    assert out["total"] is None and out["agree_rate"] is None


# --- Artifact-kind branches (summarize_order_agree_rate) ------------------------------------


def test_single_and_multi_kinds():
    single = summarize_order_agree_rate(_stats(agree=6, disagree=2, tie=2))
    assert single["kind"] == "single"
    assert single["total"] == 10 and single["agree_rate"] == 0.6
    assert single["partitions"] is None

    multi = summarize_order_agree_rate({"per_repo": [], **_stats(agree=2, disagree=1, tie=1)})
    assert multi["kind"] == "multi" and multi["partitions"] is None
    assert multi["total"] == 4 and multi["agree_rate"] == 0.5


def test_invalid_kind_returns_none_fields():
    out = summarize_order_agree_rate({})
    assert out["kind"] == "invalid"
    assert out["total"] is None and out["agree_rate"] is None
    assert out["partitions"] is None


def test_summary_always_includes_required_keys():
    for art in ({}, _stats(agree=1, disagree=0, tie=0), {"per_repo": [], **_stats()},
                {"generalization_gap": 0.1, "tuned": _stats(agree=1), "held_out": _stats(agree=1)}):
        assert _REQUIRED_KEYS <= set(summarize_order_agree_rate(art))


def test_generalization_partitions_and_overall():
    art = {
        "generalization_gap": 0.1,
        "tuned": _stats(agree=3, disagree=1, tie=0),     # total 4, rate 0.75
        "held_out": _stats(agree=2, disagree=1, tie=1),  # total 4, rate 0.5
    }
    out = summarize_order_agree_rate(art)
    assert out["kind"] == "generalization"
    assert out["agree"] == 5 and out["total"] == 8          # summed across partitions
    assert out["agree_rate"] == 0.625
    assert out["partitions"]["tuned"]["agree_rate"] == 0.75
    assert out["partitions"]["held_out"]["agree_rate"] == 0.5


def test_generalization_partial_partition_withholds_overall():
    art = {
        "generalization_gap": 0.1,
        "tuned": _stats(agree=3, disagree=1, tie=0),
        "held_out": {"judge_order_stats": {"agree": 1}},   # missing disagree/tie
    }
    out = summarize_order_agree_rate(art)
    assert out["total"] is None and out["agree_rate"] is None
    assert out["partitions"]["tuned"]["total"] == 4
    assert out["partitions"]["held_out"]["total"] is None


# --- Order agree rate headline (order_agree_rate_headline) -----------------------------------


def test_headline_single_exact_format():
    summary = summarize_order_agree_rate(_stats(agree=6, disagree=2, tie=2))
    assert order_agree_rate_headline(summary) == "order agree rate: 60.0% (6/10)"


def test_headline_generalization_appends_partition_rates():
    art = {
        "generalization_gap": 0.1,
        "tuned": _stats(agree=3, disagree=1, tie=0),
        "held_out": _stats(agree=2, disagree=1, tie=1),
    }
    summary = summarize_order_agree_rate(art)
    assert order_agree_rate_headline(summary) == (
        "order agree rate: 62.5% (5/8) [tuned 75.0%, held-out 50.0%]"
    )


def test_headline_zero_total_shows_unavailable():
    assert order_agree_rate_headline({"total": 0}) == "order agree rate: no dual-order stats available"
    assert order_agree_rate_headline({}) == "order agree rate: no dual-order stats available"


def test_headline_non_dict_summary_coerced():
    assert order_agree_rate_headline("not a dict") == "order agree rate: no dual-order stats available"


# --- Pure evaluation ------------------------------------------------------------------------


def test_summarize_does_not_mutate_artifact():
    art = {
        "generalization_gap": 0.1,
        "tuned": _stats(agree=3, disagree=1, tie=0),
        "held_out": _stats(agree=2, disagree=1, tie=1),
    }
    snapshot = copy.deepcopy(art)
    summarize_order_agree_rate(art)
    assert art == snapshot
