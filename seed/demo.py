"""Synthetic demo patient — lets you try health-os without entering your own data.

Run on a FRESH database, after migrations and `seed.load`:
    uv run python -m seed.demo

Everything here is fictional. The loader refuses to run if the database already holds a
profile or observations, so it can never mix demo values into a real record.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import text

from core.services import (
    add_allergy,
    add_diagnosis,
    add_food_log,
    add_medication,
    get_or_create_user,
    ingest_observation,
    save_meal_template,
    upsert_profile,
)

# (months ago, {raw_name: (value, unit, ref_min, ref_max)}) — LDL creeps up, vitamin D stays low
LAB_PANELS = [
    (24, {"Total cholesterol": (5.1, "mmol/L", 0, 5.2), "LDL": (3.1, "mmol/L", 0, 3.0),
          "HDL": (1.4, "mmol/L", 1.2, None), "Glucose": (5.0, "mmol/L", 3.9, 5.6),
          "Vitamin D": (18, "ng/mL", 30, 100), "TSH": (2.1, "mIU/L", 0.4, 4.0)}),
    (12, {"Total cholesterol": (5.4, "mmol/L", 0, 5.2), "LDL": (3.4, "mmol/L", 0, 3.0),
          "HDL": (1.3, "mmol/L", 1.2, None), "Glucose": (5.3, "mmol/L", 3.9, 5.6),
          "Vitamin D": (22, "ng/mL", 30, 100), "Hemoglobin": (132, "g/L", 120, 150)}),
    (1, {"Total cholesterol": (5.8, "mmol/L", 0, 5.2), "LDL": (3.8, "mmol/L", 0, 3.0),
         "HDL": (1.3, "mmol/L", 1.2, None), "Glucose": (5.5, "mmol/L", 3.9, 5.6),
         "HbA1c": (5.6, "%", 4.0, 5.7), "Vitamin D": (26, "ng/mL", 30, 100),
         "Ferritin": (35, "ng/mL", 15, 150)}),
]

MEALS = [  # (days ago, hour, meal_type, description, wellbeing, nutrients)
    (0, 8, "breakfast", "Oatmeal with banana and walnuts", "good",
     {"energy_kcal": 420, "protein": 12, "carbs": 68, "fiber": 8, "fat": 12,
      "sodium": 90, "potassium": 620, "magnesium": 110}),
    (0, 13, "lunch", "Chicken salad with olive oil, bread", "good",
     {"energy_kcal": 610, "protein": 38, "carbs": 42, "fiber": 6, "fat": 30,
      "sodium": 980, "potassium": 720, "vitamin_c": 45}),
    (1, 19, "dinner", "Pizza (3 slices), cola", "tired",
     {"energy_kcal": 1050, "protein": 36, "carbs": 130, "sugar": 42, "added_sugar": 35,
      "fat": 40, "saturated_fat": 17, "sodium": 2200, "potassium": 480}),
    (2, 8, "breakfast", "Greek yogurt, berries, honey", "good",
     {"energy_kcal": 300, "protein": 18, "carbs": 38, "sugar": 30, "fat": 8,
      "calcium": 250, "vitamin_c": 30, "sodium": 70, "potassium": 380}),
    (2, 13, "lunch", "Lentil soup, rye bread", "good",
     {"energy_kcal": 520, "protein": 26, "carbs": 78, "fiber": 16, "fat": 9,
      "iron": 6, "folate_b9": 300, "sodium": 1100, "potassium": 900}),
]


def is_empty(conn) -> bool:
    n = conn.execute(text(
        "SELECT (SELECT count(*) FROM user_profile) + (SELECT count(*) FROM observations)"
    )).scalar()
    return not n


def load_demo(conn, *, today: date | None = None) -> str:
    """Fill an empty database with the demo patient. Returns user_id."""
    if not is_empty(conn):
        raise RuntimeError("database already has a profile or observations — "
                           "the demo only loads into a fresh database")
    today = today or date.today()
    uid = get_or_create_user(conn)

    upsert_profile(conn, uid, date_of_birth=date(1985, 4, 12), sex="female",
                   blood_type="A", rh_factor="+", height_cm=168)
    add_allergy(conn, uid, "penicillin", reaction="rash", severity="moderate", verified=True)
    add_diagnosis(conn, uid, "Hypercholesterolemia", icd10_code="E78.0",
                  diagnosed_at=today - timedelta(days=30), verification_status="suspected")
    add_medication(conn, uid, "Vitamin D3", start_date=today - timedelta(days=300),
                   product_type="supplement", dose_amount=2000, dose_unit="IU", times_per_day=1)

    for months_ago, rows in LAB_PANELS:
        at = datetime.combine(today - timedelta(days=30 * months_ago), datetime.min.time())
        for name, (value, unit, lo, hi) in rows.items():
            ingest_observation(conn, uid, name, value, unit, effective_at=at,
                               ref_min=lo, ref_max=hi, time_precision="date")

    for d in range(14):  # two weeks of home blood pressure + weight
        at = datetime.combine(today - timedelta(days=d), datetime.min.time()) + timedelta(hours=8)
        ingest_observation(conn, uid, "Systolic", 128 + (d * 7) % 11, "mmHg", effective_at=at)
        ingest_observation(conn, uid, "Diastolic", 82 + (d * 5) % 7, "mmHg", effective_at=at)
        if d % 7 == 0:
            ingest_observation(conn, uid, "Weight", 68.4 - d * 0.05, "kg", effective_at=at)

    for days_ago, hour, meal_type, desc, wellbeing, nutrients in MEALS:
        at = datetime.combine(today - timedelta(days=days_ago), datetime.min.time())
        add_food_log(conn, uid, desc, eaten_at=at + timedelta(hours=hour), meal_type=meal_type,
                     wellbeing=wellbeing, nutrients=nutrients)
    save_meal_template(conn, uid, "oatmeal", meal_type="breakfast",
                       description="Oatmeal with banana and walnuts", nutrients=MEALS[0][5])
    return uid


def main() -> None:
    from core.db import engine

    with engine.begin() as conn:
        load_demo(conn)
    print("Demo patient loaded. Connect an MCP client and ask for the health summary.")


if __name__ == "__main__":
    main()
