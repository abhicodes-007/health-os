from datetime import date

from sqlalchemy import text

from core.services import (
    add_allergy,
    add_diagnosis,
    add_medication,
    ingest_observation,
    upsert_profile,
)


def test_upsert_profile(conn, user_id):
    upsert_profile(conn, user_id, date_of_birth=date(1990, 1, 1), sex="male")
    row = conn.execute(
        text("SELECT sex FROM user_profile WHERE user_id=:u"), {"u": user_id}
    ).first()
    assert row and row[0] == "male"


def test_add_allergy_failsafe_unverified(conn, user_id):
    aid = add_allergy(conn, user_id, "пеніцилін", reaction="висип", verified=False)
    row = conn.execute(text("SELECT verified FROM allergies WHERE id=:i"), {"i": aid}).first()
    assert row[0] is False  # unverified is kept (the AI treats it as an allergy — fail-safe)


def test_add_diagnosis_two_axis_status(conn, user_id):
    did = add_diagnosis(conn, user_id, "ГЕРХ", diagnosed_at=date(2023, 5, 1),
                        clinical_status="active", verification_status="suspected")
    row = conn.execute(
        text("SELECT clinical_status, verification_status FROM diagnoses WHERE id=:i"),
        {"i": did},
    ).first()
    assert row[0] == "active" and row[1] == "suspected"


def test_add_medication(conn, user_id):
    mid = add_medication(conn, user_id, "Аторвастатин", start_date=date(2024, 1, 1),
                         dose_amount=20, dose_unit="mg", times_per_day=1, atc_code="C10AA05")
    row = conn.execute(text("SELECT status FROM medications WHERE id=:i"), {"i": mid}).first()
    assert row[0] == "taking"


def test_ingest_normal_observation_approved(conn, user_id):
    res = ingest_observation(conn, user_id, "глюкоза", 5.2, "mmol/L",
                             ref_min=3.9, ref_max=5.5)
    assert res.observation_id is not None
    assert res.status == "normal"
    assert res.critical is None
    assert not res.needs_review


def test_ingest_critical_potassium_forces_review(conn, user_id):
    res = ingest_observation(conn, user_id, "калій", 6.8, "mmol/L")
    assert res.critical is not None
    assert res.status == "critical"
    assert res.needs_review
    # must land specifically as pending (forced display, not auto-approve)
    rs = conn.execute(
        text("SELECT review_status FROM observations WHERE id=:i"),
        {"i": res.observation_id},
    ).scalar()
    assert rs == "pending"


def test_ingest_unknown_name_stored_unmapped_and_flagged(conn, user_id):
    res = ingest_observation(conn, user_id, "абракадабра-показник", 1.0, "mmol/L")
    assert res.observation_id is not None and res.unmapped
    assert res.needs_review
    assert res.normalized.unknown_type
    row = conn.execute(
        text("SELECT type_id, raw_name, review_status FROM observations WHERE id=:i"),
        {"i": res.observation_id},
    ).mappings().one()
    assert row["type_id"] is None and row["raw_name"] == "абракадабра-показник"
    assert row["review_status"] == "pending"


def test_ingest_unit_gate_pending(conn, user_id):
    res = ingest_observation(conn, user_id, "глюкоза", 95.0, "невідомі/л")
    assert res.needs_review
    rs = conn.execute(
        text("SELECT review_status FROM observations WHERE id=:i"),
        {"i": res.observation_id},
    ).scalar()
    assert rs == "pending"
