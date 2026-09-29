from datetime import date

import pytest
from sqlalchemy import text

from core.health_summary import build
from seed.demo import load_demo


def test_demo_loads_into_empty_db(conn):
    uid = load_demo(conn, today=date(2026, 1, 15))
    res = build(conn, uid)
    assert res.valid, res.issues
    assert res.counts == {"allergies": 1, "active_diagnoses": 1, "current_medications": 1}
    # every demo marker is known to the seed catalog → nothing lands in the review queue
    pending = conn.execute(text(
        "SELECT count(*) FROM observations WHERE review_status <> 'approved'")).scalar()
    assert pending == 0
    assert conn.execute(text("SELECT count(*) FROM food_log")).scalar() == 5


def test_demo_refuses_non_empty_db(conn):
    load_demo(conn, today=date(2026, 1, 15))
    with pytest.raises(RuntimeError, match="fresh database"):
        load_demo(conn)
