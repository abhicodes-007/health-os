"""Meal templates: save/update, logging with portion scaling, analytics."""
from datetime import datetime, timedelta

from sqlalchemy import text

from core.services import log_from_template, save_meal_template


def test_save_and_update_template(conn, user_id):
    t1 = save_meal_template(conn, user_id, "Вівсянка", meal_type="breakfast",
                            description="вівсянка з бананом",
                            nutrients={"energy_kcal": 350, "protein": 12}, glycemic_index=55)
    # a repeat save with the same name → updates the same row (not a duplicate)
    t2 = save_meal_template(conn, user_id, "вівсянка", nutrients={"energy_kcal": 400})
    assert t1 == t2
    n = conn.execute(
        text("SELECT count(*) FROM v_meal_templates WHERE user_id=:u AND lower(name)='вівсянка'"),
        {"u": user_id},
    ).scalar()
    assert n == 1


def test_log_from_template_scales_portion(conn, user_id):
    save_meal_template(conn, user_id, "Рис", meal_type="lunch",
                       nutrients={"energy_kcal": 200, "carbs": 44})
    out = log_from_template(conn, user_id, "Рис", eaten_at=datetime(2026, 9, 23, 13, 0),
                            portion_factor=1.5)
    assert out["template"] == "Рис" and out["nutrients_saved"] == 2
    kcal = conn.execute(
        text("""SELECT amount FROM v_food_nutrients
                WHERE food_log_id=:f AND nutrient_code='energy_kcal'"""),
        {"f": out["id"]},
    ).scalar()
    assert float(kcal) == 300  # 200 × 1.5


def test_log_from_missing_template_returns_error(conn, user_id):
    out = log_from_template(conn, user_id, "НемаТакого", eaten_at=datetime(2026, 9, 23, 8, 0))
    assert "error" in out


def test_nutrition_summarize_flags(conn, user_id):
    from analytics.nutrition import summarize
    from core.services import add_food_log
    day = datetime.now() - timedelta(hours=1)  # inside the summarize(days=2) window
    add_food_log(conn, user_id, "солоне", eaten_at=day,
                 nutrients={"sodium": 3000, "vitamin_c": 10})
    res = summarize(conn, user_id, days=2)
    codes_excess = {e["nutrient"] for e in res["excess"]}
    assert "sodium" in codes_excess  # 3000 > upper_limit 2300
