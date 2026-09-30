"""Recompute missing canonical values (#11).

Rows can hold a numeric value but no `value_canonical` — stored before a synonym/conversion
existed, approved past the unit gate, or written by an importer that bypassed normalization.
Trends and analytics read `value_canonical`, so such rows are invisible there. This re-runs
unit canonicalization + conversion for them. Dry-run unless `apply=True`.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import text

from core.normalize import canonicalize_unit, convert_to_canonical


@dataclass
class RecomputeReport:
    scanned: int = 0
    fixed: Counter = field(default_factory=Counter)          # (code, unit) -> rows
    unconvertible: Counter = field(default_factory=Counter)  # (code, unit, canonical_unit) -> rows
    applied: bool = False

    @property
    def n_fixed(self) -> int:
        return sum(self.fixed.values())

    @property
    def n_unconvertible(self) -> int:
        return sum(self.unconvertible.values())


def recompute_canonical(conn, *, apply: bool = False, user_id: str | None = None) -> RecomputeReport:
    rows = conn.execute(
        text(
            """SELECT o.id, o.type_id, ot.code, ot.canonical_unit, o.value_numeric, o.unit
               FROM observations o JOIN observation_types ot ON ot.id = o.type_id
               WHERE o.value_numeric IS NOT NULL AND o.value_canonical IS NULL
                 AND o.deleted_at IS NULL AND (CAST(:u AS uuid) IS NULL OR o.user_id = CAST(:u AS uuid))"""
        ),
        {"u": user_id},
    ).mappings().all()

    report = RecomputeReport(scanned=len(rows), applied=apply)
    factor_cache: dict[tuple, float | None] = {}
    updates: list[dict] = []
    for r in rows:
        value = float(r["value_numeric"])
        if r["canonical_unit"] is None:
            canon = value                                   # dimensionless type
        else:
            unit = canonicalize_unit(r["unit"])
            if unit is None:
                canon = None
            else:
                # cache the linear map (factor, offset) per type/unit: 16k rows → a few queries
                key = (r["type_id"], unit)
                if key not in factor_cache:
                    zero = convert_to_canonical(r["type_id"], 0.0, unit, r["canonical_unit"], conn)
                    one = convert_to_canonical(r["type_id"], 1.0, unit, r["canonical_unit"], conn)
                    factor_cache[key] = None if zero is None else (one - zero, zero)
                lin = factor_cache[key]
                canon = None if lin is None else value * lin[0] + lin[1]
        if canon is None:
            report.unconvertible[(r["code"], r["unit"], r["canonical_unit"])] += 1
            continue
        report.fixed[(r["code"], r["unit"])] += 1
        updates.append({"id": r["id"], "v": canon})

    if apply and updates:
        conn.execute(text("UPDATE observations SET value_canonical = :v WHERE id = :id"), updates)
    return report


def count_missing_canonical(conn, user_id: str) -> dict:
    """Approved numeric rows without a canonical value, by ingestion channel (a health metric)."""
    rows = conn.execute(
        text(
            """SELECT s.channel, count(*) AS n
               FROM observations o JOIN ingestion_sources s ON s.id = o.source_id
               WHERE o.user_id=:u AND o.review_status='approved' AND o.deleted_at IS NULL
                 AND o.value_numeric IS NOT NULL AND o.value_canonical IS NULL
               GROUP BY s.channel ORDER BY n DESC"""
        ),
        {"u": user_id},
    ).all()
    return {"total": sum(n for _, n in rows), "by_channel": {c: n for c, n in rows}}
