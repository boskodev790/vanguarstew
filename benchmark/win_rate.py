"""Summarize challenger/baseline/tie rates from a replay artifact tally.

``judge_wlt`` reads the compact ``judge_report`` block; this utility normalizes the underlying
``tally`` counts into rates for CI dashboards.

Pure analysis: no I/O, never mutates its input, and a missing or malformed tally yields
``None`` rates rather than raising.
"""

from __future__ import annotations

import logging
import math

from benchmark.comparability import artifact_kind

logger = logging.getLogger(__name__)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _tally_counts(result: dict) -> tuple[int, int, int] | None:
    tally = result.get("tally")
    if not isinstance(tally, dict):
        return None
    counts = [tally.get(k) for k in ("challenger", "baseline", "tie")]
    if not all(_is_int(c) and c >= 0 for c in counts):
        return None
    return counts[0], counts[1], counts[2]


def _rates(challenger: int, baseline: int, tie: int) -> dict:
    """Build the rate block from challenger/baseline/tie counts (rates ``None`` when total 0)."""
    total = challenger + baseline + tie
    if total == 0:
        return {
            "total": 0, "challenger": 0, "baseline": 0, "tie": 0,
            "challenger_rate": None, "baseline_rate": None, "tie_rate": None,
        }
    return {
        "total": total,
        "challenger": challenger,
        "baseline": baseline,
        "tie": tie,
        "challenger_rate": round(challenger / total, 3),
        "baseline_rate": round(baseline / total, 3),
        "tie_rate": round(tie / total, 3),
    }


def _none_summary() -> dict:
    return {
        "total": None, "challenger": None, "baseline": None, "tie": None,
        "challenger_rate": None, "baseline_rate": None, "tie_rate": None,
    }


def _slice_summary(slice_) -> dict:
    """``total``/counts/rates for one replay slice's ``tally`` (``None`` block when malformed)."""
    counts = _tally_counts(_dict(slice_))
    if counts is None:
        return _none_summary()
    return _rates(*counts)


def _combined(tuned: dict, held_out: dict) -> dict:
    """Overall win rate across partitions — only when both carry complete tallies.

    Sums the ``challenger``/``baseline``/``tie`` counts of the two partition summaries, mirroring
    the sibling share/rate utilities (``offline_share``, ``order_agree_rate``, ...). Returns an
    all-``None`` block when either partition's counts are unavailable.
    """
    challengers = [tuned.get("challenger"), held_out.get("challenger")]
    baselines = [tuned.get("baseline"), held_out.get("baseline")]
    ties = [tuned.get("tie"), held_out.get("tie")]
    if not all(_is_int(v) for v in challengers + baselines + ties):
        return _none_summary()
    return _rates(sum(challengers), sum(baselines), sum(ties))


def summarize_win_rate(result) -> dict:
    """Return win-rate summary for a replay ``result`` artifact.

    Single- and multi-repo artifacts report a top-level tally; a ``generalization`` artifact has no
    top-level tally — each ``tuned``/``held_out`` partition carries its own — so its overall rate is
    summed across the two partitions (``None`` unless both carry complete tallies), with the
    per-partition summaries exposed under ``partitions``. This mirrors the sibling share/rate
    utilities (``offline_share``, ``order_agree_rate``, ``tie_order_share``, ...).
    """
    result = _dict(result)
    kind = artifact_kind(result)
    if kind == "generalization":
        tuned = _slice_summary(result.get("tuned"))
        held_out = _slice_summary(result.get("held_out"))
        return {
            "kind": kind,
            **_combined(tuned, held_out),
            "partitions": {"tuned": tuned, "held_out": held_out},
        }
    return {"kind": kind, **_slice_summary(result), "partitions": None}


def _fmt_rate(value) -> str:
    return f"{float(value):.1%}" if _is_number(value) else "n/a"


def win_rate_headline(summary: dict) -> str:
    """A one-line human summary of a :func:`summarize_win_rate` result."""
    summary = _dict(summary)
    total = summary.get("total")
    if not _is_int(total) or total == 0:
        return "win rate: no tally available"
    return (
        f"win rate: challenger {summary.get('challenger')}/{total} "
        f"({_fmt_rate(summary.get('challenger_rate'))}), "
        f"baseline {summary.get('baseline')}, tie {summary.get('tie')}"
    )
