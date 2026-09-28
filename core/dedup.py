"""Logical panel deduplication (plan 3.4, Phase 2).

SHA-256 only catches byte-identical files. Logical dedup: a match on (panel_date, lab,
≥70% of the same observation codes) → a review conflict, not a silent duplicate. Pure functions.
"""
from __future__ import annotations

from dataclasses import dataclass

JACCARD_THRESHOLD = 0.7


@dataclass
class DuplicateCandidate:
    panel_id: str
    jaccard: float
    reason: str


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def find_duplicate(panel_date, facility_id, codes: set[str],
                   existing: list[dict], threshold: float = JACCARD_THRESHOLD
                   ) -> DuplicateCandidate | None:
    """existing: [{panel_id, panel_date, facility_id, codes:set}].

    Duplicate = same date + same facility + Jaccard(codes) ≥ threshold.
    """
    for e in existing:
        if e["panel_date"] != panel_date:
            continue
        if facility_id is not None and e.get("facility_id") not in (None, facility_id):
            continue
        j = jaccard(codes, set(e["codes"]))
        if j >= threshold:
            return DuplicateCandidate(
                str(e["panel_id"]), j,
                f"same date {panel_date}, same facility, code overlap {j:.0%} (≥{threshold:.0%})",
            )
    return None
