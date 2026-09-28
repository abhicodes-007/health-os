"""Normalization of qualitative values (plan 3.11, Phase 2).

'не виявлено'/'neg'/'негат.' → canonical + ordinal_rank (for trends of qualitative results).
Titers '1:160' → keep the denominator for trends. Exact match of the normalized string.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import text

from core.normalize import canonicalize

_TITER = re.compile(r"^\s*1\s*[:/]\s*(\d+)\s*$")


@dataclass
class QualResult:
    canonical: str | None
    ordinal_rank: int | None
    titer_denominator: int | None
    raw: str


def parse_titer(raw: str) -> int | None:
    """'1:160' → 160 (denominator for trends). None if not a titer."""
    m = _TITER.match(raw)
    return int(m.group(1)) if m else None


def normalize_qualitative(raw: str, conn) -> QualResult:
    titer = parse_titer(raw)
    if titer is not None:
        return QualResult(None, None, titer, raw)
    canon = canonicalize(raw)
    row = conn.execute(
        text(
            """SELECT qv.canonical, qv.ordinal_rank
               FROM qualitative_synonyms qs JOIN qualitative_values qv ON qv.id=qs.value_id
               WHERE translate(lower(qs.synonym), 'ё', 'е') = :c LIMIT 1"""
        ),
        {"c": canon},
    ).first()
    if row is None:
        return QualResult(None, None, None, raw)
    return QualResult(row[0], row[1], None, raw)
