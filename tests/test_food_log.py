"""Food log: insertion (new canonical model), reading from the view, soft-delete."""
from datetime import datetime

from sqlalchemy import text

from core.services import add_food_log


def test_add_food_log_basic(conn, user_id):
    out = add_food_log(conn, user_id, "вівсянка з бананом",
                       eaten_at=datetime(2026, 9, 20, 8, 30), meal_type="breakfast",
                       wellbeing="good", glycemic_index=55)
    assert out["nutrients_saved"] == 0 and out["unknown_codes"] == []
    row = conn.execute(
        text("SELECT description, meal_type, wellbeing, glycemic_index FROM food_log WHERE id=:i"),
        {"i": out["id"]},
    ).first()
    assert row[0] == "вівсянка з бананом"
    assert row[1] == "breakfast"
    assert row[2] == "good"
    assert row[3] == 55


def test_food_log_visible_in_view(conn, user_id):
    out = add_food_log(conn, user_id, "борщ", eaten_at=datetime(2026, 9, 20, 13, 0),
                       meal_type="lunch")
    seen = conn.execute(
        text("SELECT description FROM v_food_log WHERE id=:i"), {"i": out["id"]}
    ).scalar()
    assert seen == "борщ"


def test_food_log_soft_delete_hidden_from_view(conn, user_id):
    out = add_food_log(conn, user_id, "кава", eaten_at=datetime(2026, 9, 20, 9, 0),
                       meal_type="drink")
    conn.execute(text("UPDATE food_log SET deleted_at=now() WHERE id=:i"), {"i": out["id"]})
    seen = conn.execute(
        text("SELECT description FROM v_food_log WHERE id=:i"), {"i": out["id"]}
    ).first()
    assert seen is None  # a deleted record doesn't reach the approved view
