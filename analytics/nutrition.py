"""Nutrition analytics (deterministic, zero LLM).

Reads the approved views (v_food_nutrients/v_food_log) — works under both the owner
and the readonly role.
- deficiencies/excesses: average daily %RDA + deficient(<70%)/excess(>upper_limit) flags;
- food↔wellbeing link: average GI/sugar/sodium by wellbeing category (ASSOCIATION,
  not causation — phrase carefully).
"""
from __future__ import annotations

from sqlalchemy import text


def summarize(conn, user_id: str, days: int = 30) -> dict:
    rows = conn.execute(
        text(
            """SELECT nutrient_code, name_uk, category, unit,
                      sum(amount) AS total,
                      count(DISTINCT date_trunc('day', eaten_at)) AS days_logged,
                      max(rda) AS rda, max(upper_limit) AS upper_limit
               FROM v_food_nutrients
               WHERE user_id=:u AND eaten_at >= now() - make_interval(days => :d)
               GROUP BY nutrient_code, name_uk, category, unit"""
        ),
        {"u": user_id, "d": days},
    ).mappings().all()

    nutrients, deficient, excess = [], [], []
    for r in rows:
        dl = r["days_logged"] or 1
        avg = float(r["total"]) / dl
        rda = float(r["rda"]) if r["rda"] is not None else None
        ul = float(r["upper_limit"]) if r["upper_limit"] is not None else None
        pct = round(avg / rda * 100) if rda else None
        flag = None
        if ul is not None and avg > ul:
            flag = "excess"
            excess.append({"nutrient": r["nutrient_code"], "name_uk": r["name_uk"],
                           "avg_per_day": round(avg, 1), "unit": r["unit"], "limit": ul})
        elif rda and pct is not None and pct < 70:
            flag = "deficient"
            deficient.append({"nutrient": r["nutrient_code"], "name_uk": r["name_uk"],
                              "pct_rda": pct, "avg_per_day": round(avg, 1), "unit": r["unit"]})
        nutrients.append({"nutrient": r["nutrient_code"], "name_uk": r["name_uk"],
                          "category": r["category"], "unit": r["unit"],
                          "avg_per_day": round(avg, 2), "rda": rda, "pct_rda": pct,
                          "upper_limit": ul, "flag": flag})

    deficient.sort(key=lambda x: x["pct_rda"])
    excess.sort(key=lambda x: x["avg_per_day"], reverse=True)

    # food ↔ wellbeing link (association)
    assoc = conn.execute(
        text(
            """SELECT f.wellbeing,
                      count(DISTINCT f.id) AS meals,
                      round(avg(f.glycemic_index)::numeric, 0) AS avg_gi,
                      round(avg(fn.amount) FILTER (WHERE fn.nutrient_code='sugar')::numeric, 1) AS avg_sugar,
                      round(avg(fn.amount) FILTER (WHERE fn.nutrient_code='sodium')::numeric, 0) AS avg_sodium
               FROM v_food_log f
               LEFT JOIN v_food_nutrients fn ON fn.food_log_id = f.id
               WHERE f.user_id=:u AND f.wellbeing IS NOT NULL
                 AND f.eaten_at >= now() - make_interval(days => :d)
               GROUP BY f.wellbeing ORDER BY meals DESC"""
        ),
        {"u": user_id, "d": days},
    ).mappings().all()

    return {
        "period_days": days,
        "days_logged": max((r["days_logged"] for r in rows), default=0),
        "deficient": deficient,
        "excess": excess,
        "wellbeing_association": [dict(a) for a in assoc],
        "nutrients": nutrients,
    }
