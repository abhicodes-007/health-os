"""Computed confidence (plan 4.4, step 6) — deterministic, not the model's self-reported value.

The model's self-reported confidence is decoration. Real signals:
- printed flag on the form (↑/↓/H/L) vs computed status → mismatch = low confidence;
- unit gate (no conversion) → hard failure;
- panel completeness (rows in the document vs extracted);
- learned mapping (highlight for review).

High-confidence (printed=computed + unit ok + complete + seed mapping) → candidate for
auto-commit AFTER proving quality on a golden-set eval (Phase 2). Until then — informative only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

_FLAG_MAP = {
    "h": "high", "↑": "high", "high": "high", "в": "high", "hi": "high",
    "l": "low", "↓": "low", "low": "low", "н/нижче": "low", "lo": "low",
    "n": "normal", "norm": "normal", "норма": "normal", "": None,
}


def normalize_printed_flag(flag: str | None) -> str | None:
    """Printed flag on the form → canonical status (high/low/normal) or None."""
    if not flag:
        return None
    return _FLAG_MAP.get(flag.strip().lower())


@dataclass
class ConfidenceResult:
    score: float
    needs_review: bool
    flags: list[str] = field(default_factory=list)


def score(*, printed_flag: str | None, computed_status: str | None,
          conversion_ok: bool, panel_complete: bool = True,
          learned_mapping: bool = False) -> ConfidenceResult:
    flags: list[str] = []
    s = 1.0
    needs_review = False

    if not conversion_ok:
        flags.append("unit_gate")
        s = min(s, 0.2)
        needs_review = True

    pf = normalize_printed_flag(printed_flag)
    # don't compare a critical status against the printed flag (critical is always on review)
    if pf is not None and computed_status not in (None, "critical"):
        if pf != computed_status:
            flags.append("flag_mismatch")   # printed ↑ but computed normal → suspicious
            s = min(s, 0.4)
            needs_review = True
    elif pf is None and computed_status is not None:
        flags.append("no_printed_flag")     # no cross-check of the flag
        s = min(s, 0.75)

    if not panel_complete:
        flags.append("panel_incomplete")
        s = min(s, 0.6)
        needs_review = True

    if learned_mapping:
        flags.append("learned_mapping")     # highlight for review (plan 4.4)
        s = min(s, 0.7)
        needs_review = True

    return ConfidenceResult(score=round(s, 2), needs_review=needs_review, flags=flags)
