"""Weekly report — deterministic scaffold (plan 5.3).

Data is gathered by code (zero LLM); the LLM narrative (cautious hypotheses with an
anxiety budget) is optional on top, fully in Phase 5. Includes HEALTH METRICS OF THE
SYSTEM ITSELF: pending-queue size and corrected fraction — their growth = extractor
degradation or a new lab.

"Everything stable, no action needed" is a legitimate and desirable result.
"""
from __future__ import annotations

from sqlalchemy import text

from core.recompute import count_missing_canonical


def build(conn, user_id: str, days: int = 7) -> dict:
    new_values = conn.execute(
        text(
            """SELECT ot.code, count(*) AS n FROM observations o
               JOIN observation_types ot ON ot.id=o.type_id
               WHERE o.user_id=:u AND o.review_status='approved' AND o.deleted_at IS NULL
                 AND o.created_at >= now() - make_interval(days => :d)
               GROUP BY ot.code ORDER BY n DESC"""
        ),
        {"u": user_id, "d": days},
    ).mappings().all()

    abnormal = conn.execute(
        text(
            """SELECT ot.code, o.value_canonical, o.status, o.effective_at
               FROM observations o JOIN observation_types ot ON ot.id=o.type_id
               WHERE o.user_id=:u AND o.review_status='approved' AND o.deleted_at IS NULL
                 AND o.status IN ('high','low','critical')
                 AND o.created_at >= now() - make_interval(days => :d)
               ORDER BY o.effective_at DESC LIMIT 20"""
        ),
        {"u": user_id, "d": days},
    ).mappings().all()

    # system health metrics
    pending_q = conn.execute(
        text("SELECT count(*) FROM observations WHERE user_id=:u AND review_status='pending' "
             "AND deleted_at IS NULL"),
        {"u": user_id},
    ).scalar()
    sources = conn.execute(
        text("""SELECT count(*) FILTER (WHERE corrected_fields IS NOT NULL) AS corrected,
                       count(*) FILTER (WHERE review_status='approved') AS approved
                FROM ingestion_sources WHERE user_id=:u"""),
        {"u": user_id},
    ).mappings().first()
    approved = sources["approved"] or 0
    corrected_ratio = (sources["corrected"] / approved) if approved else 0.0

    # nutrition for the week (top deficiencies/excesses) — deterministic, via the views
    from analytics.nutrition import summarize as _nutrition
    nut = _nutrition(conn, user_id, days)
    nutrition_block = {
        "days_logged": nut["days_logged"],
        "top_deficient": nut["deficient"][:3],
        "top_excess": nut["excess"][:3],
    }

    return {
        "period_days": days,
        "new_values": [dict(r) for r in new_values],
        "abnormal": [dict(r) for r in abnormal],
        "nutrition": nutrition_block,
        "system_health": {
            "pending_queue": pending_q,
            # approved numbers invisible to trends/analytics (#11) — should be 0
            "approved_without_canonical": count_missing_canonical(conn, user_id),
            "corrected_ratio": round(corrected_ratio, 3),
            "note": ("Pending queue is large — risk of 'rubber-stamp ok' (kill criterion)."
                     if (pending_q or 0) >= 10 else "Pending queue is normal."),
        },
        "stable": not abnormal and (pending_q or 0) < 10,
    }
