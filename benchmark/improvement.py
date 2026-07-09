"""Gate whether a candidate run improved enough over a baseline to adopt it.

``regression`` blocks a candidate that *drops* below a baseline; this is the opposite gate — a
promotion/adoption decision: only accept a new run as the current best if it **improves** the
headline composite by at least a margin. That is the natural rule for "should this become the
new king?" — a candidate that merely matches the baseline (or edges it by rounding noise) isn't
worth adopting, and one that improves clearly is.

``check_improvement(candidate, baseline, min_gain=…)`` decides whether ``candidate`` beats
``baseline`` by at least ``min_gain`` on the headline composite (extracted with
``benchmark.trend.headline_score`` — the top-level ``composite_mean``, or the ``tuned`` partition
for a ``--generalization`` artifact). The companion ``scripts/improvement.py`` exits non-zero
when the candidate did not improve enough.

Pure evaluation: no I/O, never mutates its inputs, and a malformed/non-dict artifact simply fails
the relevant checks rather than raising.
"""

from __future__ import annotations

import logging

from benchmark.trend import headline_score

logger = logging.getLogger(__name__)

DEFAULT_MIN_GAIN = 0.02
_CHECK_ROW_KEYS = ("name", "passed")


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _num(value):
    return f"{value:.3f}" if _is_number(value) else "n/a"


def check_improvement(candidate, baseline, min_gain: float = DEFAULT_MIN_GAIN) -> dict:
    """Decide whether ``candidate`` improved over ``baseline`` by at least ``min_gain``.

    Returns ``{"passed": bool, "checks": [{"name", "passed", "detail"}], "baseline_composite",
    "candidate_composite", "gain", "min_gain"}``. ``passed`` is True only when every check passes;
    all checks are always reported.
    """
    base_score = headline_score(baseline)
    cand_score = headline_score(candidate)
    both_scored = base_score is not None and cand_score is not None
    gain = round(cand_score - base_score, 3) if both_scored else None
    checks = []

    def add(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add("both_scored", both_scored,
        f"baseline composite {_num(base_score)}, candidate composite {_num(cand_score)}"
        if both_scored else "a composite score is missing from one artifact")

    improves = gain is not None and gain >= min_gain
    add("improves_by_margin", improves,
        f"gain {_num(gain)} >= {min_gain}" if gain is not None
        else "cannot compare composites")

    return {
        "passed": all(c["passed"] for c in checks),
        "checks": checks,
        "baseline_composite": base_score,
        "candidate_composite": cand_score,
        "gain": gain,
        "min_gain": min_gain,
    }


def _check_rows_list(checks) -> list[dict]:
    """Return improvement gate-check rows for headline / failed_checks helpers.

    ``None`` means the key is absent. An empty list means zero checks. Both are silent.
    Non-list containers (scalars, dicts, tuples, ranges, strings, etc.) are warned and
    treated as empty (never coerced). A usable row is a dict whose ``name`` is a ``str`` and
    whose ``passed`` is a ``bool``; anything else is skipped with a warning.

    Mirrors the sanitizer the other gate helpers use (``coverage``, ``component_floor``,
    ``skip_budget``) so a hand-built or deserialized ``check_improvement`` result whose
    ``checks`` is malformed degrades to "no checks" instead of crashing the helpers.
    """
    if checks is None:
        return []
    if not isinstance(checks, list):
        logger.warning(
            "improvement: checks is %s, not a list; treating as empty",
            type(checks).__name__,
        )
        return []
    rows = []
    for idx, row in enumerate(checks):
        if not isinstance(row, dict):
            logger.warning(
                "improvement: checks[%s] is %s, not an object; skipping",
                idx,
                type(row).__name__,
            )
            continue
        missing = [key for key in _CHECK_ROW_KEYS if key not in row]
        if missing:
            logger.warning(
                "improvement: checks[%s] missing required key(s) %s; skipping",
                idx,
                missing,
            )
            continue
        if not isinstance(row["name"], str):
            logger.warning(
                "improvement: checks[%s] name is %s, not str; skipping",
                idx,
                type(row["name"]).__name__,
            )
            continue
        if type(row["passed"]) is not bool:
            logger.warning(
                "improvement: checks[%s] passed is %s, not bool; skipping",
                idx,
                type(row["passed"]).__name__,
            )
            continue
        rows.append(row)
    if checks and not rows:
        logger.warning(
            "improvement: checks had %d entr%s but no usable rows",
            len(checks),
            "y" if len(checks) == 1 else "ies",
        )
    return rows


def failed_checks(result: dict) -> list:
    """The names of the checks that failed in a :func:`check_improvement` result.

    Tolerant of a malformed ``checks`` field (absent, non-list, or unusable rows): those
    entries are warned and skipped via :func:`_check_rows_list` rather than raising, matching
    the other gate helpers.
    """
    return [c["name"] for c in _check_rows_list(_dict(result).get("checks")) if not c["passed"]]


def improvement_headline(result: dict) -> str:
    """A one-line human summary of a :func:`check_improvement` result.

    When ``checks`` is missing, empty, a non-list container, or contains only unusable rows,
    returns ``"improvement: no checks evaluated"`` after logging any warnings.
    """
    result = _dict(result)
    checks = _check_rows_list(result.get("checks"))
    if not checks:
        return "improvement: no checks evaluated"
    if result.get("passed"):
        return (f"improvement: ADOPT (composite {_num(result.get('baseline_composite'))} -> "
                f"{_num(result.get('candidate_composite'))}, gain {_num(result.get('gain'))})")
    failed = failed_checks(result)
    return f"improvement: HOLD ({len(failed)}/{len(checks)} checks failed: {', '.join(failed)})"
